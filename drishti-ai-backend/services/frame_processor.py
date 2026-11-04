"""Bounded, serialized inference offloaded by callers; no cv2.VideoCapture usage."""
import io
import time
import uuid
import threading
from collections import OrderedDict
from datetime import datetime, timezone
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from ai.object_tracker import ObjectTracker
from ai.depth_estimation import DepthEstimator
from ai.obstacle_detection import ObstacleAwareness
from ai.scene_understanding import SceneUnderstanding
from services.voice_service import LOCALES, lang_value, DISCONNECTED
from services.errors import ServiceError
from database.models import VisionResponse, CameraStatus, HapticFeedback

class FrameProcessor:
    def __init__(self,settings,detector,ocr,voice,history):
        self.settings,self.detector,self.ocr,self.voice,self.history=settings,detector,ocr,voice,history
        self.lock=threading.Lock()
        self.sessions=OrderedDict()
        self.latest=None
        self.obstacles=ObstacleAwareness()
        self.scene=SceneUnderstanding()
        self.depth=DepthEstimator()
    def decode(self,data):
        if not data: raise ServiceError(422,'empty_frame','Image data is empty.')
        if len(data)>self.settings.max_upload_bytes: raise ServiceError(413,'frame_too_large','Frame exceeds upload byte limit.')
        try:
            with Image.open(io.BytesIO(data)) as image:
                w,h=image.size
                if image.format not in {'JPEG','PNG','WEBP'}: raise ServiceError(415,'image_format','Use JPEG, PNG or WebP.')
                if min(w,h)<32 or max(w,h)>self.settings.max_image_dimension or w*h>self.settings.max_image_pixels:
                    raise ServiceError(413,'frame_dimensions','Frame dimensions exceed limits or are smaller than 32 pixels.')
                image.verify()
            frame=cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
            if frame is None: raise ValueError('decode failure')
            return frame
        except ServiceError: raise
        except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError) as exc:
            raise ServiceError(422,'invalid_image','Image could not be decoded.') from exc
    def process(self,data,language,device_id,mode='detection',camera=False):
        # Do not accumulate queued inferences when CPU is busy. Caller can drop/retry frames.
        if not self.lock.acquire(blocking=False): raise ServiceError(429,'inference_busy','Processor busy. Drop this frame and send the next one.')
        try:
            start=time.monotonic()
            stamp=start
            expired=[key for key,v in self.sessions.items() if stamp-v['seen']>self.settings.session_ttl]
            for key in expired: del self.sessions[key]
            session=self.sessions.get(device_id)
            if camera and session and stamp-session['last_frame']<1/self.settings.processing_fps:
                raise ServiceError(429,'frame_throttled','Frame rate exceeded. Send 1–2 frames per second.')
            frame=self.decode(data)
            h,w=frame.shape[:2]
            lang=lang_value(language)
            detections=[] if mode=='ocr' else self.detector.detect(frame)
            if session is None:
                if len(self.sessions)>=self.settings.max_sessions: self.sessions.popitem(last=False)
                session={'tracker':ObjectTracker(),'seen':stamp,'last_frame':-float('inf')}
                self.sessions[device_id]=session
            self.sessions.move_to_end(device_id)
            session['seen']=stamp
            if camera: detections=session['tracker'].update(detections)
            self.depth.estimate(frame,detections)
            description=self.scene.describe(detections,lang) if mode in {'scene','all','navigation'} else None
            ocr=self.ocr.read(frame,lang) if mode in {'ocr','all'} else None
            if mode=='ocr': text,priority,key=ocr.voice_ready_message,'medium',f'ocr:{ocr.voice_ready_message}'
            elif mode=='scene': text,priority,key=description,'medium',f'scene:{description}'
            else: text,priority,key=self.obstacles.candidate(detections,lang)
            announcements=[]
            pending=0
            if mode in {'detection','obstacle','navigation','all'}:
                voice,announcements,pending=self.voice.offer_objects(detections,lang,device_id)
            else:
                voice=self.voice.offer(text,lang,device_id,priority,key)
            haptic=HapticFeedback()
            from collections import Counter
            counts=Counter((d.name,d.position) for d in detections)
            groups={(name,position,count) for (name,position),count in counts.items()}
            old_groups=session.get('haptic_groups',set())
            last_haptic=session.get('last_haptic',-float('inf'))
            if groups-old_groups and stamp-last_haptic>=self.settings.haptic_cooldown:
                important=any(d.priority in {'high','emergency'} for d in detections if any(key[:2]==(d.name,d.position) for key in groups-old_groups))
                haptic=HapticFeedback(vibrate=True,pattern_ms=[0,160,100,160] if important else [0,120],reason='new_or_repositioned_detection')
                session['last_haptic']=stamp
                session['haptic_groups']=groups
            elif stamp-last_haptic>=self.settings.haptic_cooldown:
                session['haptic_groups']=groups

            result=VisionResponse(event_id=str(uuid.uuid4()),device_id=device_id,language=lang,tts_locale=LOCALES[lang],
                detections=detections,scene_description=description,scene_method=self.scene.method if description else None,
                voice=voice,voice_message=voice.message,object_announcements=announcements,voice_pending_count=pending,haptic=haptic,ocr=ocr,width=w,height=h,
                inference_ms=round((time.monotonic()-start)*1000,2),warnings=self.obstacles.warnings(detections,lang) if mode!='ocr' else [])
            self.history.add(result,'android_camera' if camera else mode)
            if camera:
                session['last_frame']=time.monotonic()
                # Re-encode validated pixels; strip EXIF and cap preview size. Only latest image in RAM.
                preview=frame
                if max(h,w)>1280: preview=cv2.resize(frame,(int(w*1280/max(h,w)),int(h*1280/max(h,w))))
                ok,jpg=cv2.imencode('.jpg',preview,[cv2.IMWRITE_JPEG_QUALITY,78])
                if ok:
                    self.latest={'event_id':result.event_id,'device_id':device_id,'at':datetime.now(timezone.utc),'monotonic':time.monotonic(),'jpeg':jpg.tobytes()}
            return result
        finally: self.lock.release()
    def status(self):
        latest=self.latest
        connected=bool(latest and time.monotonic()-latest['monotonic']<=self.settings.camera_timeout)
        if latest and not connected and self.latest is latest:
            # No stale camera images remain after timeout.
            self.latest=None
        return CameraStatus(connected=connected,device_id=latest['device_id'] if latest else None,
            last_frame_at=latest['at'] if latest else None,processing_fps=self.settings.processing_fps,
            message='Android phone frames are arriving.' if connected else DISCONNECTED['en'])
    def snapshot_entry(self):
        latest=self.latest
        if not latest or time.monotonic()-latest['monotonic']>self.settings.camera_timeout:
            raise ServiceError(409,'camera_disconnected',DISCONNECTED['en'])
        return latest
    def snapshot(self):
        return self.snapshot_entry()['jpeg']
