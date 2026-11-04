import asyncio
import secrets
from typing import Annotated
from fastapi import UploadFile, Query, Request
from database.models import Language, VisionResponse, ErrorResponse
from services.errors import ServiceError

DeviceID=Annotated[str,Query(min_length=1,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')]
ERRORS={400:{'description':'Invalid request'},401:{'description':'API key missing or invalid'},413:{'description':'Image exceeds limits'},415:{'description':'Unsupported image'},422:{'description':'Image or parameter validation failed'},429:{'description':'Busy or frame rate exceeded'},503:{'description':'Required inference engine unavailable'},504:{'description':'OCR timeout'}}

for spec in ERRORS.values(): spec['model']=ErrorResponse

async def read_image(image:UploadFile,request:Request):
    try:
        data=await image.read(request.app.state.settings.max_upload_bytes+1)
    finally:
        await image.close()
    if len(data)>request.app.state.settings.max_upload_bytes:
        raise ServiceError(413,'frame_too_large','Frame exceeds upload byte limit.')
    return data

async def process(request,image,language,device_id,mode,camera=False):
    data=await read_image(image,request)
    result=await asyncio.to_thread(request.app.state.processor.process,data,language,device_id,mode,camera)
    if camera:
        request.app.state.hub.publish({'type':'detections',**result.model_dump(mode='json')})
    return result

def valid_key(expected,provided):
    return not expected or secrets.compare_digest(expected.encode(),(provided or '').encode())
