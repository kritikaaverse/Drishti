"""Validated environment configuration; no laptop camera is opened anywhere."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    app_name: str = 'Drishti'
    api_key: str = ''
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    model_path: str = str(ROOT / 'weights/yolov8n.pt')
    allow_model_download: bool = False
    inference_device: str = 'cpu'
    cpu_threads: int = Field(2, ge=1, le=16)
    confidence_threshold: float = Field(.35, ge=.05, le=1)
    inference_size: int = Field(640, ge=320, le=1280)
    max_upload_bytes: int = Field(4 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    max_image_pixels: int = Field(12000000, ge=10000, le=32000000)
    max_image_dimension: int = Field(6000, ge=640, le=12000)
    processing_fps: float = Field(2, gt=0, le=10)
    camera_timeout: float = Field(8, ge=2, le=120)
    session_ttl: float = Field(300, ge=30, le=3600)
    max_sessions: int = Field(32, ge=1, le=256)
    max_websockets: int = Field(16, ge=1, le=128)
    voice_batch_size: int = Field(4, ge=1, le=8)
    haptic_cooldown: float = Field(2, ge=.5, le=30)
    announcement_cooldown: float = Field(6, ge=1, le=60)
    repeat_after: float = Field(20, ge=2, le=300)
    database_path: str = str(ROOT / 'data/drishti.sqlite3')
    history_limit: int = Field(10000, ge=10, le=1000000)
    tesseract_cmd: str = ''
    ocr_timeout: int = Field(15, ge=2, le=90)
    @model_validator(mode='after')
    def validate_cors(self):
        if '*' in self.cors_origins.split(','):
            raise ValueError('Use explicit trusted CORS origins, not *.')
        if self.repeat_after < self.announcement_cooldown:
            raise ValueError('REPEAT_AFTER must be >= ANNOUNCEMENT_COOLDOWN')
        return self
    @property
    def origins(self):
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]

@lru_cache
def get_settings():
    return Settings()
