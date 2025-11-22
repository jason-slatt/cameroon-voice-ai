"""
Chat-related request/response schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from src.core.constants import CameroonLanguage, MAX_CHAT_HISTORY_MESSAGES


class ChatMessage(BaseModel):
    """Individual chat message"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=10000)
    language: Optional[CameroonLanguage] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request schema for chat completion"""
    user_id: UUID
    session_id: UUID
    message: str = Field(..., min_length=1, max_length=5000)
    language: Optional[CameroonLanguage] = None
    include_history: bool = Field(default=True)
    max_history_messages: int = Field(
        default=10,
        ge=1,
        le=MAX_CHAT_HISTORY_MESSAGES
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "message": "Comment puis-je commander?",
                "language": "french",
                "include_history": True,
                "max_history_messages": 10
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chat completion"""
    response_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    message: str
    language: CameroonLanguage
    tokens_used: int
    processing_time_seconds: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "response_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "message": "Pour commander, cliquez sur le bouton...",
                "language": "french",
                "tokens_used": 45,
                "processing_time_seconds": 0.8,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class ConversationHistory(BaseModel):
    """Conversation history schema"""
    session_id: UUID
    user_id: UUID
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    @validator("messages")
    def validate_message_count(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        if len(value) > MAX_CHAT_HISTORY_MESSAGES:
            return value[-MAX_CHAT_HISTORY_MESSAGES:]
        return value