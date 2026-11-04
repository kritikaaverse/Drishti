VEHICLES={'car','bus','truck','motorcycle','bicycle','train'}
ANIMALS={'dog','cat','cow','horse','sheep','bird','elephant','bear','zebra','giraffe'}
FURNITURE={'chair','bench','couch','dining table','bed'}

def category(name):
    if name=='person': return 'People'
    if name in VEHICLES: return 'Vehicles'
    if name in ANIMALS: return 'Animals'
    if name in FURNITURE: return 'Furniture'
    if name in {'traffic light','stop sign','fire hydrant','parking meter'}: return 'Infrastructure'
    return 'Objects'

def priority(name, position, area_ratio):
    # Heuristic relevance, not proximity, collision prediction or emergency certainty.
    if name=='person' or name in VEHICLES: return 'high'
    if position=='center' and area_ratio>.12: return 'high'
    if name in FURNITURE or area_ratio>.08: return 'medium'
    return 'low'

RANK={'emergency':4,'high':3,'medium':2,'low':1}
def ranked(detections):
    return sorted(detections,key=lambda d:(RANK[d.priority],d.position=='center',d.box_area_ratio,d.confidence),reverse=True)
