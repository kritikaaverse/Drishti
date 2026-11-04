import time
import pytest

def test_auth_health_and_docs(client,headers):
    assert client.get('/api/health').status_code==401
    assert client.get('/api/health',headers=headers).status_code==200
    assert client.get('/openapi.json').status_code==200
    assert client.get('/api/device/status',headers=headers).json()['source']=='android_phone'
    assert client.get('/api/device/status',headers=headers).json()['battery'] is None

def test_invalid_images_and_parameters(client,headers):
    assert client.post('/api/detection/analyze',headers=headers,files={'image':('bad.jpg',b'not an image','image/jpeg')}).status_code==422
    assert client.get('/api/detection/history?limit=999',headers=headers).status_code==422
    assert client.post('/api/ocr/read?language=xx',headers=headers,files={'image':('bad.jpg',b'bad','image/jpeg')}).status_code==422
    assert client.post('/api/camera/frame?device_id=bad/name',headers=headers,files={'image':('bad.jpg',b'bad','image/jpeg')}).status_code==422

def test_history_roundtrip(client,headers,text_image):
    if not client.app.state.detector.model: pytest.skip('Weights missing')
    r=client.post('/api/detection/analyze?device_id=history-test',headers=headers,files={'image':('text.jpg',text_image,'image/jpeg')})
    assert r.status_code==200
    h=client.get('/api/detection/history?device_id=history-test',headers=headers).json()
    assert h['records'][0]['event_id']==r.json()['event_id']
    d=client.delete('/api/detection/history?device_id=history-test',headers=headers)
    assert d.json()['deleted']>=1
    assert client.get('/api/detection/history?device_id=history-test',headers=headers).json()['total']==0

def test_frame_status_and_snapshot(client,headers,text_image):
    if not client.app.state.detector.model: pytest.skip('Weights missing')
    r=client.post('/api/camera/frame?device_id=phone-test&language=mr',headers=headers,files={'image':('phone.jpg',text_image,'image/jpeg')})
    assert r.status_code==200,r.text
    assert client.get('/api/camera/status',headers=headers).json()['connected']
    assert client.get('/api/camera/snapshot',headers=headers).headers['content-type']=='image/jpeg'
    again=client.post('/api/camera/frame?device_id=phone-test',headers=headers,files={'image':('phone.jpg',text_image,'image/jpeg')})
    assert again.status_code==429

def test_websocket_camera_and_watch(client,text_image):
    if not client.app.state.detector.model: pytest.skip('Weights missing')
    with client.websocket_connect('/api/ws/vision') as watch:
        watch.send_json({'role':'watch','api_key':'test-secret','device_id':'observer'})
        assert watch.receive_json()['type']=='ready'
        assert watch.receive_json()['type']=='camera_status'
        with client.websocket_connect('/api/ws/vision') as camera:
            camera.send_json({'role':'camera','api_key':'test-secret','device_id':'socket-phone','language':'hi'})
            assert camera.receive_json()['type']=='ready'
            assert camera.receive_json()['type']=='camera_status'
            camera.send_bytes(text_image)
            data=camera.receive_json()
            assert data['type']=='detections' and data['success']
            assert data['tts_locale']=='hi-IN'
            incoming=watch.receive_json()
            # A camera heartbeat can race the results broadcast.
            while incoming.get('type')!='detections': incoming=watch.receive_json()
            assert incoming['event_id']==data['event_id']

def test_voice_and_guidance(client,headers,text_image):
    r=client.post('/api/voice/message',headers=headers,json={'message':'सामने एक व्यक्ति है।','language':'hi','device_id':'voice-test','priority':'high'})
    assert r.status_code==200 and r.json()['tts_locale']=='hi-IN'
    assert client.post('/api/voice/message',headers=headers,json={'message':'सामने एक व्यक्ति है।','language':'hi','device_id':'voice-test','priority':'high'}).json()['voice']['suppressed']
    if not client.app.state.detector.model: return
    r=client.post('/api/navigation/guidance',headers=headers,files={'image':('text.jpg',text_image,'image/jpeg')})
    assert r.status_code==200 and r.json()['routing_available'] is False

def test_camera_expiry(client,headers,text_image):
    if not client.app.state.detector.model: pytest.skip('Weights missing')
    r=client.post('/api/camera/frame?device_id=expiry-test',headers=headers,files={'image':('frame.jpg',text_image,'image/jpeg')})
    assert r.status_code==200
    client.app.state.processor.latest['monotonic']-=100
    assert not client.get('/api/camera/status',headers=headers).json()['connected']
    assert client.get('/api/camera/snapshot',headers=headers).status_code==409

def test_invalid_auth_websocket(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/api/ws/vision') as ws:
            ws.send_json({'role':'watch','api_key':'wrong'})
            ws.receive_json()

def test_oversized_frame(client,headers):
    data=b'x'*(client.app.state.settings.max_upload_bytes+1)
    r=client.post('/api/camera/frame',headers=headers,files={'image':('big.jpg',data,'image/jpeg')})
    assert r.status_code==413

def test_detection_haptic_suppression(client,headers):
    from pathlib import Path
    if not client.app.state.detector.model: pytest.skip('Weights missing')
    image=(Path(__file__).parent/'fixtures/street.jpg').read_bytes()
    endpoint='/api/detection/analyze?device_id=haptic-test'
    first=client.post(endpoint,headers=headers,files={'image':('street.jpg',image,'image/jpeg')})
    assert first.status_code==200
    assert first.json()['haptic']['vibrate'] is True
    assert first.json()['object_announcements']
    second=client.post(endpoint,headers=headers,files={'image':('street.jpg',image,'image/jpeg')})
    assert second.json()['haptic']['vibrate'] is False
    assert second.json()['voice']['suppressed']

def test_single_use_pairing(client,headers):
    assert client.post('/api/connection/pair').status_code==401
    token=client.post('/api/connection/pair',headers=headers).json()['token']
    response=client.post('/api/connection/redeem',json={'token':token})
    assert response.status_code==200 and response.json()['api_key']=='test-secret'
    assert client.post('/api/connection/redeem',json={'token':token}).status_code==401
