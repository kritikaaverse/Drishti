"""Public API schemas. Confidence is always a fraction [0, 1]."""
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

def now():
    return datetime.now(timezone.utc)
class Language(str, Enum):
    en = 'en'
    hi = 'hi'
    mr = 'mr'
class Box(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
class Detection(BaseModel):
    name: str
    confidence: float = Field(ge=0, le=1)
    bounding_box: Box
    position: Literal['left', 'center', 'right']
    tracking_id: int | None = None
    priority: Literal['low', 'medium', 'high', 'emergency'] = 'low'
    distance: float | None = None
    distance_type: Literal['not_available'] = 'not_available'
    class_id: int
    category: str = 'Objects'
    box_area_ratio: float = Field(ge=0, le=1)
class VoiceMessage(BaseModel):
    message: str = ''
    language: Language = Language.en
    tts_locale: str = 'en-IN'
    priority: Literal['low', 'medium', 'high', 'emergency'] = 'low'
    suppressed: bool = False
class ObjectAnnouncement(BaseModel):
    name: str
    position: Literal['left','center','right']
    count: int = Field(ge=1)
    message: str
class HapticFeedback(BaseModel):
    vibrate: bool = False
    pattern_ms: list[int] = Field(default_factory=list)
    reason: str = 'no_new_detections'
    meaning: str = 'detection_attention_only_not_distance_or_safety'
class OCRResult(BaseModel):
    text: str
    language: Language
    engine_languages: str
    confidence: float | None = Field(None, ge=0, le=1)
    voice_ready_message: str
class VisionResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    event_id: str | None = None
    device_id: str | None = None
    detections: list[Detection] = Field(default_factory=list)
    scene_description: str | None = None
    scene_method: str | None = None
    voice_message: str = ''
    voice: VoiceMessage | None = None
    language: Language = Language.en
    tts_locale: str = 'en-IN'
    object_announcements: list[ObjectAnnouncement] = Field(default_factory=list)
    voice_pending_count: int = 0
    haptic: HapticFeedback = Field(default_factory=HapticFeedback)
    ocr: OCRResult | None = None
    width: int | None = None
    height: int | None = None
    inference_ms: float | None = None
    warnings: list[str] = Field(default_factory=list)
class ErrorResponse(BaseModel):
    success: bool = False
    timestamp: datetime = Field(default_factory=now)
    error: str
    code: str
class CameraStatus(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    connected: bool
    device_id: str | None = None
    source: str = 'android_phone'
    last_frame_at: datetime | None = None
    processing_fps: float
    message: str
class DeviceStatus(CameraStatus):
    camera: str = 'Android smartphone camera'
    model_loaded: bool
    model: str
    inference_device: str
    supported_classes: list[str]
    ocr_languages: list[str]
    wifi: dict | None = None
    battery: int | None = None
    sensors: dict | None = None
class HealthResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    status: Literal['ready', 'degraded']
    model_loaded: bool
    model_error: str | None = None
    ocr_languages: list[str]
    authenticated: bool
class HistoryRecord(BaseModel):
    event_id: str
    timestamp: datetime
    device_id: str
    source: str
    response: VisionResponse
class HistoryResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    records: list[HistoryRecord]
    total: int
    limit: int
    offset: int
class DeleteResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    deleted: int
class VoiceRequest(BaseModel):
    message: str = Field(min_length=1, max_length=600)
    language: Language = Language.en
    device_id: str = Field(default='android', pattern=r'^[A-Za-z0-9_-]{1,64}$')
    priority: Literal['low', 'medium', 'high', 'emergency'] = 'low'
class VoiceResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    voice: VoiceMessage
    message: str
    language: Language
    tts_locale: str
class NavigationResponse(VisionResponse):
    routing_available: bool = False
    guidance_type: str = 'camera_observation_only'
class VoiceCommand(BaseModel):
    command: str = Field(min_length=1, max_length=600)
    language: Language = Language.en
class CommandResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=now)
    response: str
    language: Language
    tts_locale: str
class SocketConfig(BaseModel):
    role: Literal['camera','watch'] = 'camera'
    device_id: str = Field(default='android', pattern=r'^[A-Za-z0-9_-]{1,64}$')
    language: Language = Language.en
    api_key: str = Field(default='', max_length=512)
    mode: Literal['detection','all','obstacle','scene'] = 'obstacle'
