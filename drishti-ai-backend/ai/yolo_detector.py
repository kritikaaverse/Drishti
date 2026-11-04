import logging
from pathlib import Path
from database.models import Detection, Box
from services.priority_manager import category, priority

log=logging.getLogger(__name__)
class YOLODetector:
    def __init__(self, settings):
        self.settings=settings
        self.model=None
        self.error=None
        self.names={}
    def load(self):
        try:
            import torch
            torch.set_num_threads(self.settings.cpu_threads)
            from ultralytics import YOLO
            path=Path(self.settings.model_path)
            if not path.is_file() and not self.settings.allow_model_download:
                raise RuntimeError('Model weights missing. Run python scripts/download_models.py before starting.')
            if not path.is_file(): path.parent.mkdir(parents=True,exist_ok=True)
            self.model=YOLO(str(path))
            self.names=self.model.names
            self.error=None
            log.info('YOLO loaded once: %s on %s',path.name,self.settings.inference_device)
        except Exception as exc:
            self.model=None
            self.error=str(exc)
            log.exception('YOLO unavailable; inference endpoints will return 503')
    def detect(self, frame):
        if self.model is None:
            from services.errors import ServiceError
            raise ServiceError(503,'model_unavailable',self.error or 'YOLO unavailable')
        h,w=frame.shape[:2]
        result=self.model.predict(source=frame,conf=self.settings.confidence_threshold,
                                  imgsz=self.settings.inference_size,device=self.settings.inference_device,
                                  verbose=False,max_det=100)[0]
        found=[]
        if result.boxes is None: return found
        for row in result.boxes.data.cpu().tolist():
            x1,y1,x2,y2,confidence,cls=row[:6]
            x1,x2=sorted((max(0,min(w,x1)),max(0,min(w,x2))))
            y1,y2=sorted((max(0,min(h,y1)),max(0,min(h,y2))))
            if x2<=x1 or y2<=y1: continue
            center=(x1+x2)/2/w
            pos='left' if center<1/3 else 'right' if center>2/3 else 'center'
            name=self.names[int(cls)]
            area=(x2-x1)*(y2-y1)/(w*h)
            found.append(Detection(name=name,class_id=int(cls),confidence=round(confidence,5),
                         bounding_box=Box(x1=x1,y1=y1,x2=x2,y2=y2),position=pos,
                         box_area_ratio=area,priority=priority(name,pos,area),category=category(name)))
        return found
