import asyncio
from fastapi import APIRouter, UploadFile, File, Query, Request
from api.common import process, DeviceID, ERRORS
from database.models import Language, VisionResponse, HistoryResponse, DeleteResponse
router=APIRouter(prefix='/api',tags=['Detection'])

@router.post('/detection/analyze',response_model=VisionResponse,responses=ERRORS,summary='Run real YOLO detection on an uploaded image')
async def analyze(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='upload'):
    return await process(request,image,language,device_id,'detection')

@router.post('/detection/analyze-all',response_model=VisionResponse,responses=ERRORS,summary='YOLO, OCR and evidence-bound scene summary; requires all OCR packs for selected language')
async def analyze_all(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='upload'):
    return await process(request,image,language,device_id,'all')

@router.get('/detection/history',response_model=HistoryResponse,responses=ERRORS,summary='Paginated stored inference events, never stored camera images')
async def history(request:Request,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),device_id:DeviceID|None=None):
    return await asyncio.to_thread(request.app.state.history.get,limit,offset,device_id)

@router.delete('/detection/history',response_model=DeleteResponse,responses=ERRORS,summary='Permanently delete inference records, optionally restricted to one device')
async def delete_history(request:Request,device_id:DeviceID|None=None):
    count=await asyncio.to_thread(request.app.state.history.delete,device_id)
    return DeleteResponse(deleted=count)
