import pytest
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import io

def test_real_english_ocr(client,headers,text_image):
    if 'eng' not in client.app.state.ocr.available: pytest.skip('English Tesseract pack not installed')
    r=client.post('/api/ocr/read?language=en',headers=headers,files={'image':('text.jpg',text_image,'image/jpeg')})
    assert r.status_code==200,r.text
    text=r.json()['ocr']['text'].upper()
    assert 'BUS' in text and '24' in text
    assert r.json()['ocr']['engine_languages']=='eng'

@pytest.mark.parametrize('language,pack',[('hi','hin'),('mr','mar')])
def test_installed_devanagari_engine(client,headers,text_image,language,pack):
    # Verifies actual requested language engine runs; not an OCR quality benchmark.
    if pack not in client.app.state.ocr.available: pytest.skip(f'{pack} not installed')
    r=client.post(f'/api/ocr/read?language={language}',headers=headers,files={'image':('text.jpg',text_image,'image/jpeg')})
    assert r.status_code==200
    assert r.json()['ocr']['engine_languages']==f'{pack}+eng'
    assert r.json()['tts_locale']==f'{language}-IN'

@pytest.mark.parametrize('language,word',[('hi','स्टॉप'),('mr','थांबा')])
def test_real_devanagari_text(client,headers,language,word):
    pack={'hi':'hin','mr':'mar'}[language]
    if pack not in client.app.state.ocr.available: pytest.skip('Language pack missing')
    image=Path(__file__).parent/f'fixtures/ocr-{language}.png'
    response=client.post(f'/api/ocr/read?language={language}',headers=headers,files={'image':(image.name,image.read_bytes(),'image/png')})
    assert response.status_code==200
    assert word in response.json()['ocr']['text']
