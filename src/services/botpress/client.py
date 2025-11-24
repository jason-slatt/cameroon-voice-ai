# src/services/botpress/client.py
"""
Botpress client - send messages back to WhatsApp
"""
import httpx
from typing import Optional

from src.core.exception import WhatsAppError
from src.core.config import settings
from src.core.logging import logger


class BotpressClient:
    """Send messages via Botpress to WhatsApp"""
    
    def __init__(self):
        self.base_url = settings.BOTPRESS_URL
        self.bot_id = settings.BOTPRESS_BOT_ID
        self.api_token = settings.BOTPRESS_API_TOKEN
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "x-bot-id": self.bot_id,
                "Content-Type": "application/json",
            }
        )
        
        logger.info("✅ Botpress client initialized")
    
    async def send_text(
        self,
        conversation_id: str,
        text: str,
    ) -> bool:
        """Send text message back to WhatsApp user"""
        try:
            url = f"{self.base_url}/v1/chat/messages"
            
            payload = {
                "conversationId": conversation_id,
                "payload": {
                    "type": "text",
                    "text": text
                }
            }
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"✅ Text sent to conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send text: {e}")
            raise WhatsAppError(f"Failed to send message: {e}")
    
    async def send_audio(
        self,
        conversation_id: str,
        audio_url: str,
    ) -> bool:
        """Send audio message back to WhatsApp user"""
        try:
            url = f"{self.base_url}/v1/chat/messages"
            
            payload = {
                "conversationId": conversation_id,
                "payload": {
                    "type": "audio",
                    "audio": audio_url,
                    "title": "Voice Response"
                }
            }
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"✅ Audio sent to conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            raise WhatsAppError(f"Failed to send audio: {e}")
    
    async def download_audio(self, audio_url: str, save_path: str) -> str:
        """Download audio file from Botpress"""
        try:
            response = await self.client.get(audio_url)
            response.raise_for_status()
            
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"✅ Audio downloaded to {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
            raise WhatsAppError(f"Failed to download audio: {e}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()