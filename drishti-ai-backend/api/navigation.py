from fastapi import APIRouter,UploadFile,File,Request
from api.common import process,DeviceID,ERRORS
from database.models import Language,VisionResponse,NavigationResponse
router=APIRouter(prefix='/api',tags=['Obstacle and camera guidance'])
@router.post('/obstacle/detect',response_model=VisionResponse,responses=ERRORS,summary='Prioritize possible obstacles by relevance; not a collision or safe-path guarantee')
async def obstacles(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='obstacle'):
    return await process(request,image,language,device_id,'obstacle')
@router.post('/navigation/guidance',response_model=NavigationResponse,responses=ERRORS,summary='Cautious image-based observation only; no GPS routing or safe-crossing decisions')
async def guidance(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='navigation'):
    result=await process(request,image,language,device_id,'navigation')
    return NavigationResponse(**result.model_dump())
