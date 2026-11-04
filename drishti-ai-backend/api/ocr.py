from fastapi import APIRouter,UploadFile,File,Request
from api.common import process,DeviceID,ERRORS
from database.models import Language,VisionResponse
router=APIRouter(prefix='/api/ocr',tags=['OCR'])
@router.post('/read',response_model=VisionResponse,responses=ERRORS,summary='Read actual printed English, Hindi or Marathi text using local Tesseract')
async def read(request:Request,image:UploadFile=File(...),language:Language=Language.en,device_id:DeviceID='ocr'):
    return await process(request,image,language,device_id,'ocr')
