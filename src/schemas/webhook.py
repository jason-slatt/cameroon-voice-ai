# src/schemas/webhook.py
"""
WhatsApp webhook schemas
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class WhatsAppProfile(BaseModel):
    """User profile from WhatsApp"""
    name: str


class WhatsAppAudio(BaseModel):
    """Audio message details"""
    id: str
    mime_type: str
    sha256: str
    voice: bool = Field(default=True)


class WhatsAppText(BaseModel):
    """Text message details"""
    body: str


class WhatsAppMessage(BaseModel):
    """Individual WhatsApp message"""
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: Literal["text", "audio", "image", "video", "document"]
    text: Optional[WhatsAppText] = None
    audio: Optional[WhatsAppAudio] = None


class WhatsAppContact(BaseModel):
    """Contact information"""
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppValue(BaseModel):
    """Webhook value payload"""
    messaging_product: str
    metadata: dict
    contacts: Optional[list[WhatsAppContact]] = None
    messages: Optional[list[WhatsAppMessage]] = None


class WhatsAppChange(BaseModel):
    """Webhook change"""
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    """Webhook entry"""
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhook(BaseModel):
    """Complete WhatsApp webhook payload"""
    object: str
    entry: list[WhatsAppEntry]


class WebhookResponse(BaseModel):
    """Response sent back to WhatsApp"""
    success: bool
    message_id: Optional[str] = None
    status: str
    processing_time: Optional[float] = None