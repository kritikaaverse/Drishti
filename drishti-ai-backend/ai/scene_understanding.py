"""Evidence-bound object summary. This is NOT a vision-language model.
Does not infer rooms, children, road safety, light colors or unseen obstacles.
"""
from collections import Counter
from services.voice_service import NAMES, NO_OBJECTS, lang_value

class SceneUnderstanding:
    method='detected_objects_summary'
    def describe(self, detections, language):
        lang=lang_value(language)
        if not detections: return NO_OBJECTS[lang]
        counts=Counter(d.name for d in detections)
        entries=[]
        for name,count in counts.most_common(8):
            label=name if lang=='en' else NAMES.get(name,(name,name))[0 if lang=='hi' else 1]
            entries.append(f'{count} {label}')
        objects=', '.join(entries)
        if lang=='en': return f'The camera recognizes: {objects}. The wider scene cannot be confirmed from object detections alone.'
        if lang=='hi': return f'कैमरे में पहचानी गई वस्तुएं: {objects}। केवल वस्तुओं की पहचान से पूरे दृश्य की पुष्टि नहीं की जा सकती।'
        return f'कॅमेऱ्यात ओळखलेल्या वस्तू: {objects}. केवळ वस्तूंच्या ओळखीवरून संपूर्ण दृश्याची खात्री करता येत नाही.'
