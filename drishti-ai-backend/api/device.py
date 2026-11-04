from fastapi import APIRouter,Request
from database.models import DeviceStatus,HealthResponse
from api.common import ERRORS
router=APIRouter(prefix='/api',tags=['Device'])
@router.get('/health',response_model=HealthResponse,responses=ERRORS,summary='Report actual detector and OCR readiness')
async def health(request:Request):
    s=request.app.state
    return HealthResponse(status='ready' if s.detector.model is not None else 'degraded',model_loaded=s.detector.model is not None,
                          model_error=s.detector.error,ocr_languages=s.ocr.available,authenticated=bool(s.settings.api_key))
@router.get('/device/status',response_model=DeviceStatus,responses=ERRORS,summary='Phone frame heartbeat and actual engine capabilities; no guessed battery or Wi-Fi telemetry')
async def status(request:Request):
    s=request.app.state
    camera=s.processor.status()
    return DeviceStatus(**camera.model_dump(),model_loaded=s.detector.model is not None,model=s.settings.model_path.split('/')[-1],
                        inference_device=s.settings.inference_device,supported_classes=list(s.detector.names.values()),ocr_languages=s.ocr.available)
