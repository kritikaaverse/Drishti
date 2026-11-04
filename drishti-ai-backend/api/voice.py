import asyncio
from fastapi import APIRouter,Request
from api.common import ERRORS
from database.models import VoiceRequest,VoiceResponse,VoiceCommand,CommandResponse
from services.voice_service import LOCALES,DISCONNECTED
router=APIRouter(prefix='/api/voice',tags=['Voice'])
@router.post('/message',response_model=VoiceResponse,responses=ERRORS,summary='Prepare supplied text for Android TextToSpeech with duplicate suppression')
async def message(body:VoiceRequest,request:Request):
    voice=await asyncio.to_thread(request.app.state.voice.offer,body.message,body.language,body.device_id,body.priority)
    return VoiceResponse(voice=voice,message=voice.message,language=voice.language,tts_locale=voice.tts_locale)
@router.post('/command',response_model=CommandResponse,responses=ERRORS,summary='Local status command adapter; not an LLM or speech recognizer')
async def command(body:VoiceCommand,request:Request):
    # No invented scene answers. Direct users to actual camera processing.
    lang=body.language.value
    status=request.app.state.processor.status()
    text=DISCONNECTED[lang] if not status.connected else {
        'en':'Phone camera is connected. Send a frame for detection, or upload an image for OCR and scene summaries.',
        'hi':'फोन कैमरा जुड़ा है। पहचान के लिए फ्रेम भेजें, या पाठ और दृश्य सारांश के लिए चित्र अपलोड करें।',
        'mr':'फोन कॅमेरा जोडलेला आहे. ओळखीसाठी फ्रेम पाठवा किंवा मजकूर आणि दृश्य सारांशासाठी चित्र अपलोड करा.'}[lang]
    return CommandResponse(response=text,language=lang,tts_locale=LOCALES[lang])
