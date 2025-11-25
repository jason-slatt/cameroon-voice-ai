"""API Response schemas"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class IntentInfo(BaseModel):
    """Detected intent information"""
    intent: str
    confidence: float


class FlowInfo(BaseModel):
    """Current conversation flow information"""
    flow_type: Optional[str] = None
    step: Optional[str] = None
    is_complete: bool = False


class AssistantResponse(BaseModel):
    """Response from the assistant"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = Field(..., description="Assistant's response message")
    user_id: str = Field(..., alias="userId")
    conversation_id: str = Field(..., alias="conversationId")
    
    # Input handling
    transcribed_text: Optional[str] = Field(
        None, 
        alias="transcribedText", 
        description="Transcribed text if voice input"
    )
    
    # Audio response
    audio_url: Optional[str] = Field(
        None, 
        alias="audioUrl", 
        description="URL to response audio"
    )
    audio_duration_ms: Optional[int] = Field(
        None,
        alias="audioDurationMs",
        description="Duration of audio in milliseconds"
    )
    
    # Metadata
    intent: Optional[IntentInfo] = None
    flow: Optional[FlowInfo] = None
    
    # Transaction data if applicable
    transaction_data: Optional[Dict[str, Any]] = Field(None, alias="transactionData")
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = Field(None, alias="processingTimeMs")
    
    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    """Error response"""
    status: ResponseStatus = ResponseStatus.ERROR
    error_code: str = Field(..., alias="errorCode")
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str
    services: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)