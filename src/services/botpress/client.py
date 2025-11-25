# src/services/botpress/client.py
from typing import Any, Dict
import httpx
from pathlib import Path

from src.core.logging import logger
from src.core.config import settings


class BotpressClient:
    def __init__(self) -> None:
        self.base_url = settings.BOTPRESS_URL.rstrip("/")
        self.token = settings.BOTPRESS_API_TOKEN
        self._client = httpx.AsyncClient(timeout=30)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
        }

    async def send_text(self, conversation_id: str, text: str) -> None:
        """
        Send a text message to a conversation.
        """
        url = f"{self.base_url}/conversations/{conversation_id}/messages"

        payload = {
            "type": "text",
            "text": text,
        }

        logger.info("📤 Sending text to Botpress: %s", payload)

        response = await self._client.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"payload": payload},
        )
        response.raise_for_status()

    async def send_audio(self, conversation_id: str, audio_path: str | Path) -> None:
        """
        Send an audio file (voice reply) to Botpress.
        """
        url = f"{self.base_url}/conversations/{conversation_id}/messages"

        audio_path = Path(audio_path)
        logger.info("🎧 Sending audio to Botpress: %s", audio_path)

        # You may need to adapt "type" and field names
        # depending on how your Botpress WhatsApp integration expects media.
        files = {
            "file": (
                audio_path.name,
                audio_path.read_bytes(),
                "audio/ogg",  # or audio/wav depending on what you send
            )
        }

        data = {
            "type": "audio",
        }

        response = await self._client.post(
            url,
            headers=self._headers(),
            data=data,
            files=files,
        )
        response.raise_for_status()

    async def download_audio(self, audio_url: str, dest_path: str) -> None:
        logger.info("📥 Downloading audio from %s", audio_url)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            Path(dest_path).write_bytes(response.content)
