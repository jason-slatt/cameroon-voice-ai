"""Speech-to-Text service using Whisper"""

import whisper
import numpy as np
import tempfile
import os
from typing import Optional
from functools import lru_cache

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class STTService:
    """Speech-to-Text service using OpenAI Whisper"""
    
    def __init__(self):
        self.model = None
        self._loaded = False
    
    def _ensure_loaded(self):
        """Lazy load the model"""
        if not self._loaded:
            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self.model = whisper.load_model(settings.WHISPER_MODEL)
            self._loaded = True
            logger.info("Whisper model loaded successfully")
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text or None if failed
        """
        self._ensure_loaded()
        
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            try:
                # Transcribe
                result = self.model.transcribe(temp_path, fp16=False)
                text = result["text"].strip()
                
                logger.info(f"Transcribed: {text[:100]}...")
                return text
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    async def transcribe_from_array(self, audio_array: np.ndarray) -> Optional[str]:
        """
        Transcribe numpy audio array to text.
        
        Args:
            audio_array: Audio as numpy array (float32, normalized)
            
        Returns:
            Transcribed text or None if failed
        """
        self._ensure_loaded()
        
        try:
            result = self.model.transcribe(audio_array, fp16=False)
            text = result["text"].strip()
            
            logger.info(f"Transcribed: {text[:100]}...")
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None


@lru_cache()
def get_stt_service() -> STTService:
    """Get cached STT service instance"""
    return STTService()