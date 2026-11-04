import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import pytest
from config import Settings
from main import create_app
from fastapi.testclient import TestClient

@pytest.fixture(scope='session')
def client(tmp_path_factory):
    settings=Settings(database_path=str(tmp_path_factory.mktemp('db')/'test.sqlite3'),api_key='test-secret',cors_origins='http://testserver',processing_fps=10)
    with TestClient(create_app(settings)) as client:
        yield client
@pytest.fixture
def headers(): return {'X-API-Key':'test-secret'}
@pytest.fixture
def text_image():
    image=np.full((300,1000,3),255,dtype=np.uint8)
    cv2.putText(image,'BUS STOP ROUTE 24',(35,165),cv2.FONT_HERSHEY_SIMPLEX,2,(0,0,0),3,cv2.LINE_AA)
    return cv2.imencode('.jpg',image)[1].tobytes()
