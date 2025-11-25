"""Audio processing utilities"""

import httpx
from typing import Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def download_audio(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download audio from URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Failed to download audio from {url}: {e}")
        return None