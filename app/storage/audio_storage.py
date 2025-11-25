"""Audio file storage service"""

import os
import uuid
import aiofiles
from datetime import datetime
from typing import Optional
from pathlib import Path
from functools import lru_cache

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AudioStorageService:
    """Service for storing and retrieving audio files"""
    
    def __init__(self, base_path: str = "audio_files", base_url: Optional[str] = None):
        self.base_path = Path(base_path)
        self.base_url = base_url or settings.AUDIO_BASE_URL
        
        # Create directories
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "responses").mkdir(exist_ok=True)
        (self.base_path / "uploads").mkdir(exist_ok=True)
    
    def _generate_filename(self, prefix: str = "audio", extension: str = "wav") -> str:
        """Generate a unique filename"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{unique_id}.{extension}"
    
    async def save_response_audio(
        self,
        audio_data: bytes,
        conversation_id: str,
        extension: str = "wav",
    ) -> str:
        """
        Save response audio and return the URL.
        
        Args:
            audio_data: Audio bytes
            conversation_id: Conversation ID for organization
            extension: File extension
            
        Returns:
            URL to the saved audio file
        """
        filename = self._generate_filename("response", extension)
        
        # Create conversation directory
        conv_dir = self.base_path / "responses" / conversation_id
        conv_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = conv_dir / filename
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(audio_data)
        
        logger.info(f"Saved response audio: {file_path}")
        
        # Return URL
        relative_path = f"responses/{conversation_id}/{filename}"
        return f"{self.base_url}/{relative_path}"
    
    async def get_audio(self, file_path: str) -> Optional[bytes]:
        """
        Get audio file by path.
        
        Args:
            file_path: Relative path to audio file
            
        Returns:
            Audio bytes or None if not found
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return None
        
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()
    
    async def delete_audio(self, file_path: str) -> bool:
        """
        Delete an audio file.
        
        Args:
            file_path: Relative path to audio file
            
        Returns:
            True if deleted, False otherwise
        """
        full_path = self.base_path / file_path
        
        if full_path.exists():
            os.unlink(full_path)
            return True
        
        return False
    
    async def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Clean up old audio files.
        
        Args:
            max_age_hours: Maximum age in hours
        """
        import time
        
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        deleted_count = 0
        
        for subdir in ["responses", "uploads"]:
            dir_path = self.base_path / subdir
            if not dir_path.exists():
                continue
            
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    file_path = Path(root) / filename
                    try:
                        file_age = current_time - file_path.stat().st_mtime
                        
                        if file_age > max_age_seconds:
                            os.unlink(file_path)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Error cleaning up file {file_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old audio files")


@lru_cache()
def get_audio_storage() -> AudioStorageService:
    """Get cached audio storage instance"""
    return AudioStorageService(
        base_path=settings.AUDIO_STORAGE_PATH,
        base_url=settings.AUDIO_BASE_URL,
    )