# src/schemas/botpress.py
"""
Botpress webhook schemas
These define what Botpress sends to your API
"""
from typing import Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field


class BotpressUser(BaseModel):
    """User who sent the message"""
    id: str
    name: Optional[str] = None
    pictureUrl: Optional[str] = None


class BotpressTextPayload(BaseModel):
    """Text message payload"""
    type: Literal["text"]
    text: str


class BotpressAudioPayload(BaseModel):
    """Audio/voice message payload"""
    type: Literal["audio", "voice"]
    audio: str  # URL to audio file
    title: Optional[str] = None


class BotpressFilePayload(BaseModel):
    """File message payload"""
    type: Literal["file"]
    file: str  # URL to file


class BotpressMessage(BaseModel):
    """
    Message from Botpress
    Can be text, audio, or file
    """
    id: str
    conversationId: str
    userId: str
    type: str
    payload: dict  # We'll parse this based on type
    createdAt: datetime = Field(default_factory=datetime.utcnow)


class BotpressIncomingWebhook(BaseModel):
    """
    Complete webhook payload from Botpress
    This is what hits your /webhook/botpress endpoint
    """
    event: Literal["message.created", "conversation.started"]
    message: Optional[BotpressMessage] = None
    conversationId: str
    userId: str
    botId: str


class BotpressOutgoingMessage(BaseModel):
    """
    Message you send BACK to Botpress
    """
    conversationId: str
    userId: str
    type: Literal["text", "audio", "file"]
    payload: dict


class BotpressTextMessage(BaseModel):
    """Send text to user"""
    text: str
    
    def to_payload(self, conversation_id: str, user_id: str) -> BotpressOutgoingMessage:
        return BotpressOutgoingMessage(
            conversationId=conversation_id,
            userId=user_id,
            type="text",
            payload={"type": "text", "text": self.text}
        )


class BotpressAudioMessage(BaseModel):
    """Send audio to user"""
    audio: str  # URL or base64
    title: Optional[str] = "Voice Response"
    
    def to_payload(self, conversation_id: str, user_id: str) -> BotpressOutgoingMessage:
        return BotpressOutgoingMessage(
            conversationId=conversation_id,
            userId=user_id,
            type="audio",
            payload={
                "type": "audio",
                "audio": self.audio,
                "title": self.title
            }
        )