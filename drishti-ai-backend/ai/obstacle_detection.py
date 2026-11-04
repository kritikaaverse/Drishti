from services.priority_manager import ranked, VEHICLES
from services.voice_service import object_message, NO_OBJECTS, TRAFFIC, lang_value

class ObstacleAwareness:
    def warnings(self, detections, language):
        lang=lang_value(language)
        warnings=[]
        if any(d.name in VEHICLES|{'traffic light','stop sign'} for d in detections):
            warnings.append(TRAFFIC[lang])
        warnings.append({'en':'Camera observations are uncertain; continue using your primary mobility aid.',
                         'hi':'कैमरे की पहचान अनिश्चित हो सकती है। अपने मुख्य चलने के सहायक साधन का उपयोग जारी रखें।',
                         'mr':'कॅमेऱ्याची ओळख अनिश्चित असू शकते. तुमचे मुख्य चालण्याचे सहाय्य वापरत राहा.'}[lang])
        return warnings
    def candidate(self, detections, language):
        ordered=ranked(detections)
        if not ordered: return NO_OBJECTS[lang_value(language)], 'low', 'no_objects'
        target=ordered[0]
        return object_message(target,language), target.priority, f'{target.name}:{target.position}'
