"""Short multilingual TTS payloads with bounded per-device cooldown state."""
import time
from collections import OrderedDict
from threading import Lock
from database.models import Language, VoiceMessage, ObjectAnnouncement
from services.priority_manager import RANK, VEHICLES

LOCALES={'en':'en-IN','hi':'hi-IN','mr':'mr-IN'}
NAMES={
 'person':('व्यक्ति','व्यक्ती'), 'chair':('कुर्सी','खुर्ची'), 'car':('कार','कार'),
 'bus':('बस','बस'), 'truck':('ट्रक','ट्रक'), 'bicycle':('साइकिल','सायकल'),
 'motorcycle':('मोटरसाइकिल','मोटारसायकल'), 'dog':('कुत्ता','कुत्रा'), 'cat':('बिल्ली','मांजर'),
 'cow':('गाय','गाय'), 'bird':('पक्षी','पक्षी'), 'bottle':('बोतल','बाटली'),
 'dining table':('मेज','टेबल'), 'bench':('बेंच','बाक'), 'couch':('सोफ़ा','सोफा'),
 'traffic light':('ट्रैफिक लाइट','वाहतूक दिवा'), 'stop sign':('रुकने का संकेत','थांबण्याचे चिन्ह'),
 'backpack':('बैग','पिशवी'), 'handbag':('बैग','पिशवी'), 'laptop':('लैपटॉप','लॅपटॉप'),
 'cell phone':('मोबाइल फोन','मोबाइल फोन'), 'bed':('बिस्तर','पलंग'),
}
NO_OBJECTS={
 'en':'No objects recognized. This does not mean the path is safe.',
 'hi':'कोई वस्तु पहचानी नहीं गई। इसका मतलब यह नहीं है कि रास्ता सुरक्षित है।',
 'mr':'कोणतीही वस्तू ओळखली नाही. याचा अर्थ मार्ग सुरक्षित आहे असा नाही.'}
TRAFFIC={
 'en':'Traffic is visible. Do not rely on this camera to decide when to cross.',
 'hi':'यातायात दिखाई दे रहा है। सड़क पार करने का निर्णय केवल इस कैमरे से न लें।',
 'mr':'वाहतूक दिसत आहे. रस्ता ओलांडण्याचा निर्णय फक्त या कॅमेऱ्यावरून घेऊ नका.'}
DISCONNECTED={
 'en':'Phone camera disconnected. Visual assistance is unavailable.',
 'hi':'फोन कैमरा जुड़ा नहीं है। दृश्य सहायता उपलब्ध नहीं है।',
 'mr':'फोन कॅमेरा जोडलेला नाही. दृश्य सहाय्य उपलब्ध नाही.'}

def lang_value(language): return language.value if isinstance(language,Language) else language

def object_message(d, language):
    lang=lang_value(language)
    if lang=='en':
        noun='Vehicle' if d.name in VEHICLES else d.name.capitalize()
        return f'{noun} ' + {'left':'on your left.','center':'ahead.','right':'on your right.'}[d.position]
    noun=NAMES.get(d.name,('वस्तु','वस्तू'))[0 if lang=='hi' else 1]
    if lang=='hi':
        return {'left':f'आपके बाईं ओर {noun} है।','center':f'सामने {noun} है।','right':f'आपके दाईं ओर {noun} है।'}[d.position]
    return {'left':f'तुमच्या डाव्या बाजूला {noun} आहे.','center':f'समोर {noun} आहे.','right':f'तुमच्या उजव्या बाजूला {noun} आहे.'}[d.position]

class VoiceService:
    def __init__(self, settings):
        self.settings=settings
        self.states=OrderedDict()
        self.object_states=OrderedDict()
        self.lock=Lock()
    def offer(self, message, language, device_id, priority='low', fingerprint=None):
        lang=lang_value(language)
        stamp=time.monotonic()
        key=(device_id,lang)
        fingerprint=fingerprint or message
        with self.lock:
            state=self.states.pop(key,None)
            if state and stamp-state['seen']>self.settings.session_ttl: state=None
            last=state['last'] if state else -float('inf')
            old_rank=state['rank'] if state else 0
            recent=state['recent'] if state else {}
            recent={k:v for k,v in recent.items() if stamp-v<self.settings.repeat_after}
            # Emergency bypasses ordinary cooldown, but never its own duplicate suppression.
            duplicate=fingerprint in recent
            cooldown=stamp-last<self.settings.announcement_cooldown
            blocked=duplicate or (cooldown and RANK[priority]<=old_rank)
            if not blocked:
                recent[fingerprint]=stamp
                last=stamp
                old_rank=RANK[priority]
            self.states[key]={'last':last,'seen':stamp,'rank':old_rank,'recent':recent}
            while len(self.states)>self.settings.max_sessions*3: self.states.popitem(last=False)
        return VoiceMessage(message='' if blocked else message,language=lang,tts_locale=LOCALES[lang],priority=priority,suppressed=blocked)

    def offer_objects(self, detections, language, device_id):
        """Fair batches of distinct class/position groups. Visible unsaid groups come first.
        No stale off-camera narration, no 'path safe' inference, and no individual identity claim.
        """
        from services.priority_manager import ranked
        lang=lang_value(language)
        grouped={}
        for d in ranked(detections):
            item=grouped.setdefault((d.name,d.position),{'d':d,'count':0})
            item['count']+=1
        if not grouped:
            voice=self.offer(NO_OBJECTS[lang],lang,device_id,'low','no_objects')
            return voice,[],0
        grouped={(k[0],k[1],v['count']):v for k,v in grouped.items()}
        stamp=time.monotonic()
        with self.lock:
            key=(device_id,lang)
            state=self.object_states.pop(key,None)
            if not state or stamp-state['seen']>self.settings.session_ttl:
                state={'last':-float('inf'),'rank':0,'announced':{},'seen':stamp}
            state['seen']=stamp
            announced=state['announced']
            state['announced']=announced={k:v for k,v in announced.items() if stamp-v<self.settings.session_ttl}
            eligible=[(k,v) for k,v in grouped.items() if stamp-announced.get(k,-float('inf'))>=self.settings.repeat_after]
            # Never-announced groups cannot starve behind repeatedly visible high-priority groups.
            eligible.sort(key=lambda pair:(announced.get(pair[0],-float('inf')),-RANK[pair[1]['d'].priority]))
            if stamp-state['last']<self.settings.announcement_cooldown:
                eligible=[pair for pair in eligible if RANK[pair[1]['d'].priority]>state['rank']]
            selected=eligible[:self.settings.voice_batch_size]
            messages=[]
            priority='low'
            for fingerprint,item in selected:
                d,count=item['d'],item['count']
                message=object_message(d,lang)
                if count>1:
                    if lang=='en':
                        noun='people' if d.name=='person' else d.name
                        message=f'{count} {noun} detected '+{'center':'ahead.','left':'on your left.','right':'on your right.'}[d.position]
                    else:
                        noun=NAMES.get(d.name,('वस्तु','वस्तू'))[0 if lang=='hi' else 1]
                        if lang=='hi': message={'center':f'सामने {count} {noun} दिखाई दे रहे हैं।','left':f'बाईं ओर {count} {noun} दिखाई दे रहे हैं।','right':f'दाईं ओर {count} {noun} दिखाई दे रहे हैं।'}[d.position]
                        else: message={'center':f'समोर {count} {noun} दिसत आहेत.','left':f'डाव्या बाजूला {count} {noun} दिसत आहेत.','right':f'उजव्या बाजूला {count} {noun} दिसत आहेत.'}[d.position]
                messages.append(ObjectAnnouncement(name=d.name,position=d.position,count=count,message=message))
                announced[fingerprint]=stamp
                if RANK[d.priority]>RANK[priority]: priority=d.priority
            if messages:
                state['last']=stamp
                state['rank']=RANK[priority]
            self.object_states[key]=state
            while len(self.object_states)>self.settings.max_sessions*3:self.object_states.popitem(last=False)
            pending=sum(1 for k in grouped if k not in announced or stamp-announced[k]>=self.settings.repeat_after)
        return VoiceMessage(message=' '.join(m.message for m in messages),language=lang,tts_locale=LOCALES[lang],priority=priority,suppressed=not messages),messages,pending
