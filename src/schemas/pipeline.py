# src/schemas/pipeline.py
"""
End-to-end pipeline request/response schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.core.constants import CameroonLanguage


class PipelineRequest(BaseModel):
    """Full voice-to-voice pipeline request"""
    audio_id: UUID
    user_id: UUID
    session_id: Optional[UUID] = None
    input_language: Optional[CameroonLanguage] = None
    output_language: Optional[CameroonLanguage] = None
    detect_language: bool = Field(default=True)
    include_history: bool = Field(default=True)
    speaker_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "audio_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "session_id": "123e4567-e89b-12d3-a456-426614174002",
                "detect_language": True,
                "include_history": True
            }
        }


class PipelineStepMetrics(BaseModel):
    """Metrics for individual pipeline steps"""
    transcription_time: float = Field(description="Time in seconds")
    llm_inference_time: float = Field(description="Time in seconds")
    tts_generation_time: float = Field(description="Time in seconds")
    total_time: float = Field(description="Total time in seconds")


class PipelineResponse(BaseModel):
    """Full pipeline response"""
    pipeline_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    
    # Input
    transcription: str
    detected_input_language: CameroonLanguage
    transcription_confidence: float
    
    # Processing
    llm_response: str
    output_language: CameroonLanguage
    
    # Output
    audio_url: str
    audio_duration_seconds: float
    
    # Metrics
    metrics: PipelineStepMetrics
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "transcription": "Bonjour, comment allez-vous?",
                "detected_input_language": "french",
                "transcription_confidence": 0.95,
                "llm_response": "Je vais très bien, merci! Comment puis-je vous aider?",
                "output_language": "french",
                "audio_url": "https://storage.example.com/audio/123.mp3",
                "audio_duration_seconds": 3.5,
                "metrics": {
                    "transcription_time": 1.2,
                    "llm_inference_time": 0.8,
                    "tts_generation_time": 1.5,
                    "total_time": 3.5
                }
            }
        }


class TextPipelineRequest(BaseModel):
    """Text-only pipeline (no TTS)"""
    message: str = Field(..., min_length=1, max_length=5000)
    user_id: UUID
    session_id: Optional[UUID] = None
    language: Optional[CameroonLanguage] = None
    include_history: bool = Field(default=True)


class TextPipelineResponse(BaseModel):
    """Text-only pipeline response"""
    response_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    response: str
    language: CameroonLanguage
    processing_time_seconds: float
    created_at: datetime = Field(default_factory=datetime.utcnow)