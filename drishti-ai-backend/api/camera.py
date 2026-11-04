import asyncio
import json
import logging
from fastapi import APIRouter,UploadFile,File,Request,WebSocket,WebSocketDisconnect
from fastapi.responses import Response,StreamingResponse
from pydantic import ValidationError
from api.common import process,DeviceID,ERRORS,valid_key
from database.models import Language,VisionResponse,CameraStatus,SocketConfig,ErrorResponse
from services.errors import ServiceError

log=logging.getLogger(__name__)
router=APIRouter(prefix='/api',tags=['Android camera'])
class VisionHub:
    def __init__(self): self.watchers=set(); self.connections=0; self.camera_devices=set()
    def publish(self,message):
        for queue in tuple(self.watchers):
            if queue.full():
                try: queue.get_nowait()
                except asyncio.QueueEmpty: pass
            queue.put_nowait(message)

@router.post('/camera/frame',response_model=VisionResponse,responses=ERRORS,summary='Accept one Android JPEG frame; bounded CPU backpressure and per-device FPS limit')
async def frame(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='android'):
    return await process(request,image,language,device_id,'obstacle',camera=True)
@router.get('/camera/status',response_model=CameraStatus,responses=ERRORS)
async def camera_status(request:Request): return request.app.state.processor.status()
@router.get('/camera/snapshot',responses={200:{'content':{'image/jpeg':{}},'description':'Latest actual Android frame, RAM only'},**ERRORS})
async def snapshot(request:Request):
    entry=request.app.state.processor.snapshot_entry()
    data,event_id=entry['jpeg'],entry['event_id']
    return Response(data,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Drishti-Event-Id':event_id})
@router.get('/camera/stream',responses={200:{'description':'Latest phone frames as MJPEG; no local webcam'},**ERRORS})
async def stream(request:Request):
    request.app.state.processor.snapshot()  # Fail before sending headers if disconnected.
    async def generate():
        last=None
        while not await request.is_disconnected():
            latest=request.app.state.processor.latest
            if not request.app.state.processor.status().connected: break
            if latest and latest['monotonic']!=last:
                last=latest['monotonic']
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+latest['jpeg']+b'\r\n'
            await asyncio.sleep(.2)
    return StreamingResponse(generate(),media_type='multipart/x-mixed-replace; boundary=frame',headers={'Cache-Control':'no-store'})

@router.websocket('/ws/vision')
async def vision(socket:WebSocket):
    state=socket.app.state
    settings,hub=state.settings,state.hub
    origin=socket.headers.get('origin')
    if origin and origin not in settings.origins:
        await socket.close(code=1008); return
    if hub.connections>=settings.max_websockets:
        await socket.close(code=1013); return
    await socket.accept()
    hub.connections+=1
    queue=None
    config=None
    owns_camera=False
    try:
        try:
            initial=await asyncio.wait_for(socket.receive_text(),timeout=10)
            if len(initial)>2048: raise ValueError('Configuration exceeds 2 KB')
            config=SocketConfig.model_validate_json(initial)
        except (ValueError,ValidationError,asyncio.TimeoutError):
            await socket.send_json(ErrorResponse(error='Send a valid JSON configuration first.',code='invalid_config').model_dump(mode='json'))
            await socket.close(code=1008); return
        if not valid_key(settings.api_key,config.api_key):
            await socket.close(code=1008); return
        if config.role=='camera':
            if config.device_id in hub.camera_devices:
                await socket.send_json(ErrorResponse(error='This device already has an active camera session.',code='duplicate_device').model_dump(mode='json'))
                await socket.close(code=1008); return
            hub.camera_devices.add(config.device_id)
            owns_camera=True
        await socket.send_json({'type':'ready','role':config.role,'processing_fps':settings.processing_fps,'max_upload_bytes':settings.max_upload_bytes,'device_id':config.device_id})
        await socket.send_json({'type':'camera_status',**state.processor.status().model_dump(mode='json')})
        if config.role=='watch':
            queue=asyncio.Queue(maxsize=1)
            hub.watchers.add(queue)
            while True:
                received=asyncio.create_task(socket.receive())
                outgoing=asyncio.create_task(queue.get())
                try:
                    done,pending=await asyncio.wait([received,outgoing],return_when=asyncio.FIRST_COMPLETED,timeout=25)
                    for task in pending: task.cancel()
                    await asyncio.gather(*pending,return_exceptions=True)
                    if not done:
                        await socket.send_json({'type':'heartbeat'}); continue
                    if received in done:
                        packet=received.result()
                        if packet['type']=='websocket.disconnect': break
                        if packet.get('bytes') is not None:
                            await socket.send_json(ErrorResponse(error='Watch clients cannot upload frames.',code='watch_only').model_dump(mode='json'))
                    if outgoing in done: await socket.send_json(outgoing.result())
                finally:
                    for task in (received,outgoing):
                        if not task.done(): task.cancel()
                    await asyncio.gather(received,outgoing,return_exceptions=True)
        else:
            while True:
                packet=await asyncio.wait_for(socket.receive(),timeout=60)
                if packet['type']=='websocket.disconnect': break
                raw=packet.get('bytes')
                if raw is None:
                    await socket.send_json(ErrorResponse(error='Send binary JPEG frames after configuration.',code='binary_required').model_dump(mode='json')); continue
                try:
                    result=await asyncio.to_thread(state.processor.process,raw,config.language,config.device_id,config.mode,True)
                    message={'type':'detections',**result.model_dump(mode='json')}
                    await socket.send_json(message)
                    hub.publish(message)
                except ServiceError as exc:
                    await socket.send_json(ErrorResponse(error=exc.message,code=exc.code).model_dump(mode='json'))
    except (WebSocketDisconnect,asyncio.TimeoutError): pass
    except Exception:
        log.exception('WebSocket processing failed (no image or key logged)')
        try: await socket.send_json(ErrorResponse(error='Frame processing failed.',code='internal_error').model_dump(mode='json'))
        except Exception: pass
    finally:
        if queue is not None: hub.watchers.discard(queue)
        if owns_camera: hub.camera_devices.discard(config.device_id)
        hub.connections-=1
        # Disconnection is established from frame freshness rather than a stale socket.
        try: await socket.close()
        except Exception: pass
