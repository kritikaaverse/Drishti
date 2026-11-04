"""Lightweight per-device class-aware greedy IoU tracker (not ByteTrack).
IDs are best-effort frame associations, never person identities. Missed tracks expire.
"""
from dataclasses import dataclass
import time

@dataclass
class Track:
    class_id: int
    box: tuple
    seen: float

def iou(a,b):
    x1,y1,x2,y2=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    intersection=max(0,x2-x1)*max(0,y2-y1)
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0

class ObjectTracker:
    def __init__(self, ttl=3, threshold=.25):
        self.ttl,self.threshold=ttl,threshold
        self.tracks={}
        self.next_id=1
    def update(self, detections):
        stamp=time.monotonic()
        self.tracks={k:t for k,t in self.tracks.items() if stamp-t.seen<self.ttl}
        available=set(self.tracks)
        # Match all candidates globally by IoU rather than reusing an ID twice.
        candidates=[]
        for index,d in enumerate(detections):
            box=tuple(d.bounding_box.model_dump().values())
            for key in available:
                t=self.tracks[key]
                if t.class_id==d.class_id:
                    score=iou(box,t.box)
                    if score>=self.threshold: candidates.append((score,index,key))
        assigned={}
        for _,index,key in sorted(candidates,reverse=True):
            if index not in assigned and key in available:
                assigned[index]=key
                available.remove(key)
        for index,d in enumerate(detections):
            key=assigned.get(index)
            if key is None:
                key=self.next_id
                self.next_id+=1
            d.tracking_id=key
            self.tracks[key]=Track(d.class_id,tuple(d.bounding_box.model_dump().values()),stamp)
        return detections
