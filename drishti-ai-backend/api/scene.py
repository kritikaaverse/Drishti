from fastapi import APIRouter,UploadFile,File,Request
from api.common import process,DeviceID,ERRORS
from database.models import Language,VisionResponse
router=APIRouter(prefix='/api/scene',tags=['Scene'])
@router.post('/describe',response_model=VisionResponse,responses=ERRORS,summary='Summarize only real detected objects; not a VLM-generated detailed scene')
async def describe(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='scene'):
    return await process(request,image,language,device_id,'scene')
