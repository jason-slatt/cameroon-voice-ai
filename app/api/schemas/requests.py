"""API Request schemas"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Union
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class BaseMessageRequest(BaseModel):
    """Base message request"""
    user_id: str = Field(..., alias="userId", description="Unique user identifier")
    conversation_id: str = Field(..., alias="conversationId", description="Conversation session ID")
    phone_number: str = Field(..., alias="phoneNumber", description="User's phone number")
    
    class Config:
        populate_by_name = True


class VoiceMessageRequest(BaseMessageRequest):
    """Voice message request with audio URL"""
    audio_url: HttpUrl = Field(..., alias="audioUrl", description="URL to the audio file")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "userId": "user123",
                "conversationId": "conv456",
                "phoneNumber": "+237699446699",
                "audioUrl": "https://files.example.com/audio.oga"
            }
        }


class TextMessageRequest(BaseMessageRequest):
    """Text message request"""
    text: str = Field(..., min_length=1, max_length=1000, description="User's text message")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "userId": "user123",
                "conversationId": "conv456",
                "phoneNumber": "+237699446699",
                "text": "I want to create an account"
            }
        }


# Union type for either voice or text
MessageRequest = Union[VoiceMessageRequest, TextMessageRequest]