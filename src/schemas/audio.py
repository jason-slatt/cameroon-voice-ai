"""
Audio-related request/response schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from src.core.constants import (
    CameroonLanguage,
    MAX_AUDIO_SIZE_MB,
    SUPPORTED_AUDIO_FORMATS,
)


class AudioUploadRequest(BaseModel):
    """Request schema for audio upload"""
    language: Optional[CameroonLanguage] = None
    user_id: UUID
    session_id: Optional[UUID] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "language": "bameka",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }


class TranscriptionRequest(BaseModel):
    """Request schema for transcription"""
    audio_id: UUID
    language: Optional[CameroonLanguage] = None
    enable_language_detection: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "audio_id": "123e4567-e89b-12d3-a456-426614174000",
                "language": "bameka",
                "enable_language_detection": True
            }
        }


class TranscriptionResponse(BaseModel):
    """Response schema for transcription"""
    transcription_id: UUID = Field(default_factory=uuid4)
    audio_id: UUID
    text: str
    detected_language: CameroonLanguage
    confidence: float = Field(ge=0.0, le=1.0)
    duration_seconds: float
    processing_time_seconds: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "transcription_id": "123e4567-e89b-12d3-a456-426614174000",
                "audio_id": "123e4567-e89b-12d3-a456-426614174001",
                "text": "Bonjour, comment allez-vous?",
                "detected_language": "french",
                "confidence": 0.95,
                "duration_seconds": 5.2,
                "processing_time_seconds": 1.3,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class AudioMetadata(BaseModel):
    """Metadata for audio files"""
    audio_id: UUID
    file_path: str
    format: str
    size_bytes: int
    duration_seconds: float
    sample_rate: int
    channels: int
    uploaded_at: datetime
    
    @validator("format")
    def validate_format(cls, value: str) -> str:
        if value.lower() not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(
                f"Format must be one of {SUPPORTED_AUDIO_FORMATS}"
            )
        return value.lower()
    
    @validator("size_bytes")
    def validate_size(cls, value: int) -> int:
        max_size_bytes = MAX_AUDIO_SIZE_MB * 1024 * 1024
        if value > max_size_bytes:
            raise ValueError(f"Audio size exceeds {MAX_AUDIO_SIZE_MB}MB")
        return value