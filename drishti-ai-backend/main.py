"""Run: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import HTTPConnection
from fastapi.openapi.utils import get_openapi
from fastapi import Security, Depends
from starlette.exceptions import HTTPException
from config import get_settings,ROOT
from database.db import Database
from database.models import ErrorResponse
from services.history_service import HistoryService
from services.voice_service import VoiceService
from services.frame_processor import FrameProcessor
from services.errors import ServiceError
from services.body_limit import BodyLimitMiddleware
from ai.yolo_detector import YOLODetector
from ai.ocr_engine import OCREngine
from api import camera,detection,ocr,scene,navigation,voice,device,connection
from api.common import valid_key

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
log=logging.getLogger('drishti')
async def auth(connection:HTTPConnection):
    if connection.scope['type']=='websocket':
        return  # WebSockets authenticate their first JSON packet, never a URL query string.
    if not valid_key(connection.app.state.settings.api_key,connection.headers.get('X-API-Key')):
        raise ServiceError(401,'unauthorized','A valid X-API-Key header is required.')

async def camera_monitor(app):
    previous=None
    while True:
        status=app.state.processor.status()
        current=(status.connected,status.device_id)
        if current!=previous:
            app.state.hub.publish({'type':'camera_status',**status.model_dump(mode='json')})
            previous=current
        await asyncio.sleep(1)

def create_app(settings=None):
    settings=settings or get_settings()
    @asynccontextmanager
    async def lifespan(app):
        db=Database(settings.database_path)
        await asyncio.to_thread(db.initialize)
        detector=YOLODetector(settings)
        await asyncio.to_thread(detector.load)
        ocr_engine=OCREngine(settings)
        await asyncio.to_thread(ocr_engine.inspect)
        app.state.detector,app.state.ocr=detector,ocr_engine
        app.state.history=HistoryService(db,settings.history_limit)
        app.state.voice=VoiceService(settings)
        app.state.processor=FrameProcessor(settings,detector,ocr_engine,app.state.voice,app.state.history)
        app.state.hub=camera.VisionHub()
        app.state.pairing=connection.PairingStore()
        if not settings.api_key: log.warning('API key disabled. Trusted local development only. Set API_KEY before network exposure.')
        task=asyncio.create_task(camera_monitor(app))
        yield
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        app.state.processor.latest=None
    app=FastAPI(title='Drishti · Android Vision Backend',version='1.0.0',lifespan=lifespan,
        description='Local, CPU-first assistive prototype. Android is the camera. No path-safety guarantees, no fabricated distances. TTS is spoken on the client.')
    app.state.settings=settings
    app.add_middleware(BodyLimitMiddleware,max_bytes=settings.max_upload_bytes+131072)
    app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=False,
                       allow_methods=['GET','POST','DELETE'],expose_headers=['X-Drishti-Event-Id'],allow_headers=['Content-Type','X-API-Key'])
    @app.middleware('http')
    async def guard_and_log(request,call_next):
        start=time.monotonic()
        length=request.headers.get('content-length','0')
        try: too_large=int(length)>settings.max_upload_bytes+131072
        except ValueError: too_large=True
        if too_large:
            return JSONResponse(ErrorResponse(error='Request body too large.',code='request_too_large').model_dump(mode='json'),status_code=413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        # Never log query strings, image content, API keys, or recognized private text.
        log.info('%s %s %s %.1fms',request.method,request.url.path,response.status_code,(time.monotonic()-start)*1000)
        return response
    @app.exception_handler(ServiceError)
    async def service_error(request,exc):
        return JSONResponse(ErrorResponse(error=exc.message,code=exc.code).model_dump(mode='json'),status_code=exc.status,
                            headers={'Retry-After':'1'} if exc.status==429 else None)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        fields=', '.join('.'.join(map(str,e['loc'])) for e in exc.errors())
        return JSONResponse(ErrorResponse(error=f'Invalid request field(s): {fields}',code='validation_error').model_dump(mode='json'),status_code=422)
    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        return JSONResponse(ErrorResponse(error=str(exc.detail),code='http_error').model_dump(mode='json'),status_code=exc.status_code)
    @app.exception_handler(Exception)
    async def unexpected(request,exc):
        log.exception('Unhandled backend error')
        return JSONResponse(ErrorResponse(error='Processing failed; inspect server logs.',code='internal_error').model_dump(mode='json'),status_code=500)
    for module in (camera,detection,ocr,scene,navigation,voice,device):
        app.include_router(module.router,dependencies=[Depends(auth)])
    app.include_router(connection.routes(auth))
    @app.get('/',include_in_schema=False)
    async def root():
        return {'name':'Drishti','docs':'/docs','camera_sender':'/camera-sender','primary_camera':'Android smartphone','safety':'Assistive prototype. Never infer a safe path from absent detections.'}
    @app.get('/camera-sender',include_in_schema=False)
    async def sender(): return FileResponse(ROOT/'static/camera-sender.html')
    def documented_schema():
        if app.openapi_schema: return app.openapi_schema
        schema=get_openapi(title=app.title,version=app.version,description=app.description,routes=app.routes)
        schema.setdefault('components',{}).setdefault('securitySchemes',{})['APIKey']={'type':'apiKey','in':'header','name':'X-API-Key'}
        for path,methods in schema['paths'].items():
            if path.startswith('/api/') and path!='/api/connection/redeem':
                for operation in methods.values():
                    if isinstance(operation,dict): operation['security']=[{'APIKey':[]}]
        app.openapi_schema=schema
        return schema
    app.openapi=documented_schema
    return app

app=create_app()
