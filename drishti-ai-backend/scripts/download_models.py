"""Explicit one-time download. Do not download untrusted model files."""
import hashlib
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    target=ROOT/'weights/yolov8n.pt'
    target.parent.mkdir(exist_ok=True)
    if not target.exists():
        url='https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt'
        print('Downloading official Ultralytics YOLOv8n weights:',url)
        temporary=target.with_suffix('.download')
        try:
            urllib.request.urlretrieve(url,temporary)
            temporary.replace(target)
        finally: temporary.unlink(missing_ok=True)
    print(target)
    print('SHA256:',hashlib.sha256(target.read_bytes()).hexdigest())
    print('Review Ultralytics AGPL-3.0 / enterprise licensing before distribution.')
if __name__=='__main__': main()
