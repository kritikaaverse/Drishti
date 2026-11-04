"""Cross-platform single-worker launcher with bounded WebSocket frames."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import uvicorn
from config import get_settings
if __name__=='__main__':
    s=get_settings()
    uvicorn.run('main:app',host='0.0.0.0',port=8000,workers=1,ws_max_size=s.max_upload_bytes,ws_max_queue=1,log_level='info')
