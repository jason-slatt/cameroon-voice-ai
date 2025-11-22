"""
TTS-related request/response schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from src.core.constants import CameroonLanguage, MAX_TTS_TEXT_LENGTH


class TTSRequest(BaseModel):
    """Request schema for TTS generation"""
    text: str = Field(..., min_length=1, max_length=MAX_TTS_TEXT_LENGTH)
    language: CameroonLanguage
    user_id: UUID
    session_id: Optional[UUID] = None
    speaker_id: Optional[str] = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    
    @validator("text")
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Text cannot be empty or whitespace only")
        return cleaned
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Bonjour, comment puis-je vous aider?",
                "language": "french",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "speaker_id": "default_french_female",
                "speed": 1.0,
                "pitch": 1.0
            }
        }


class TTSResponse(BaseModel):
    """Response schema for TTS generation"""
    audio_id: UUID = Field(default_factory=uuid4)
    audio_url: str
    format: str = Field(default="mp3")
    duration_seconds: float
    file_size_bytes: int
    processing_time_seconds: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "audio_id": "123e4567-e89b-12d3-a456-426614174000",
                "audio_url": "https://storage.example.com/audio/123.mp3",
                "format": "mp3",
                "duration_seconds": 4.5,
                "file_size_bytes": 72000,
                "processing_time_seconds": 1.2,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }