import cv2
import numpy as np
import pytesseract
from database.models import OCRResult
from services.errors import ServiceError
from services.voice_service import lang_value

PACKS={'en':'eng','hi':'hin+eng','mr':'mar+eng'}
class OCREngine:
    def __init__(self, settings):
        self.settings=settings
        if settings.tesseract_cmd: pytesseract.pytesseract.tesseract_cmd=settings.tesseract_cmd
        self.available=[]
    def inspect(self):
        try: self.available=pytesseract.get_languages(config='')
        except Exception: self.available=[]
    def read(self, frame, language):
        lang=lang_value(language)
        packs=PACKS[lang]
        if not set(packs.split('+'))<=set(self.available):
            raise ServiceError(503,'ocr_unavailable',f'Tesseract or language packs missing: {packs}. Install them and restart.')
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        # Keep original aspect and enlarge small text without unbounded OCR input.
        h,w=gray.shape
        scale=min(2,1800/max(h,w))
        if scale!=1: gray=cv2.resize(gray,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC if scale>1 else cv2.INTER_AREA)
        try:
            data=pytesseract.image_to_data(gray,lang=packs,config='--oem 3 --psm 3',
                                           output_type=pytesseract.Output.DICT,timeout=self.settings.ocr_timeout)
        except RuntimeError as exc: raise ServiceError(504,'ocr_timeout','OCR exceeded its time limit.') from exc
        except pytesseract.TesseractError as exc: raise ServiceError(503,'ocr_failed','Tesseract could not read the image.') from exc
        lines={}
        scores=[]
        for i,text in enumerate(data['text']):
            text=text.strip()
            confidence=float(data['conf'][i])
            if text and confidence>=0:
                key=(data['page_num'][i],data['block_num'][i],data['par_num'][i],data['line_num'][i])
                lines.setdefault(key,[]).append(text)
                scores.append(confidence/100)
        text='\n'.join(' '.join(words) for words in lines.values())
        empty={'en':'No readable text recognized.','hi':'पढ़ने योग्य पाठ पहचाना नहीं गया।','mr':'वाचता येणारा मजकूर ओळखला नाही.'}[lang]
        return OCRResult(text=text,language=lang,engine_languages=packs,
                         confidence=round(float(np.mean(scores)),4) if scores else None,
                         voice_ready_message=text[:600] if text else empty)
