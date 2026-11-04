from pathlib import Path
import pytest
from database.models import Detection,Box
from ai.object_tracker import ObjectTracker
from ai.scene_understanding import SceneUnderstanding
from config import Settings
from services.voice_service import VoiceService
from services.priority_manager import priority

def detection(position='center'):
    return Detection(name='person',class_id=0,confidence=.9,bounding_box=Box(x1=10,y1=10,x2=100,y2=180),position=position,box_area_ratio=.1,priority='high')

def test_tracker_and_priority():
    tracker=ObjectTracker()
    a=tracker.update([detection()])[0]
    b=tracker.update([detection()])[0]
    assert a.tracking_id==b.tracking_id
    assert priority('car','center',.1)=='high'
    assert a.distance is None

def test_voice_duplicate_and_meaningful_change():
    voice=VoiceService(Settings())
    first=voice.offer('Person ahead.','en','test','high')
    second=voice.offer('Person ahead.','en','test','high')
    assert first.message and second.suppressed and not second.message
    urgent=voice.offer('Emergency test message.','en','test','emergency')
    assert urgent.message
    assert voice.offer('Emergency test message.','en','test','emergency').suppressed
    assert voice.offer('Person ahead.','hi','test','high').tts_locale=='hi-IN'

def test_evidence_bound_scene():
    scene=SceneUnderstanding()
    text=scene.describe([detection()],'en')
    assert 'person' in text and 'room' not in text and 'chair' not in text
    assert 'does not mean the path is safe' in scene.describe([],'en')

def test_real_yolo_inference(client,headers,text_image):
    if not client.app.state.detector.model: pytest.skip('Real YOLO weights not installed')
    response=client.post('/api/detection/analyze',headers=headers,files={'image':('text.jpg',text_image,'image/jpeg')})
    assert response.status_code==200
    data=response.json()
    assert data['event_id'] and data['inference_ms']>0
    for d in data['detections']:
        assert 0<=d['confidence']<=1 and d['distance'] is None
        assert d['position'] in ('left','center','right')

def test_real_photo_if_provided(client,headers):
    path=Path(__file__).parent/'fixtures/street.jpg'
    if not path.exists(): pytest.skip('Optional photo fixture not provided')
    if not client.app.state.detector.model: pytest.skip('Weights missing')
    response=client.post('/api/detection/analyze-all?language=hi',headers=headers,files={'image':('street.jpg',path.read_bytes(),'image/jpeg')})
    assert response.status_code==200,response.text
    data=response.json()
    assert data['detections']  # Nonempty actual model output on bundled illustrative photo.
    assert data['scene_method']=='detected_objects_summary'
    assert all(d['distance'] is None for d in data['detections'])

def test_all_object_groups_are_announced_in_fair_batches():
    settings=Settings(voice_batch_size=2,announcement_cooldown=1,repeat_after=20)
    voice=VoiceService(settings)
    objects=[]
    for i,name in enumerate(['person','chair','car','bottle','dog']):
        d=detection(); d.name=name;d.class_id=i;objects.append(d)
    first,groups,pending=voice.offer_objects(objects,'hi','all-objects')
    assert len(groups)==2 and pending==3
    assert first.tts_locale=='hi-IN'
    seen={a.name for a in groups}
    state=voice.object_states[('all-objects','hi')]
    state['last']-=2
    _,groups,pending=voice.offer_objects(objects,'hi','all-objects')
    seen.update(a.name for a in groups)
    assert len(groups)==2 and pending==1
    state['last']-=2
    _,groups,pending=voice.offer_objects(objects,'hi','all-objects')
    seen.update(a.name for a in groups)
    assert seen=={'person','chair','car','bottle','dog'} and pending==0
    duplicate,groups,_=voice.offer_objects(objects,'hi','all-objects')
    assert duplicate.suppressed and not groups

def test_repeated_people_are_counted():
    voice=VoiceService(Settings())
    message,groups,_=voice.offer_objects([detection(),detection()],'en','count-test')
    assert groups[0].count==2
    assert '2 people' in message.message
