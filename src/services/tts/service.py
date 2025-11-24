# src/services/tts/service.py
"""
TTS service - Text to Speech
"""
import asyncio
from pathlib import Path
from typing import Optional
import time
import uuid

from TTS.api import TTS

from src.core.exception import TTSGenerationError
from src.core.config import settings
from src.core.constants import CameroonLanguage
from src.core.logging import logger


class TTSService:
    """Text-to-Speech service"""
    
    def __init__(self):
        self.model = None
        self._is_ready = False
        self.output_dir = settings.AUDIO_STORAGE_PATH / "tts_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self) -> None:
        """Load TTS model"""
        if self._is_ready:
            return
            
        logger.info("Loading TTS model...")
        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_sync)
        
        load_time = time.time() - start_time
        logger.info(f"✅ TTS loaded in {load_time:.2f}s")
        self._is_ready = True
        
    def _load_model_sync(self) -> None:
        """Load model"""
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self.model = TTS(model_name)
        
        if settings.DEVICE == "cuda":
            self.model.to("cuda")
        
    async def synthesize(
        self,
        text: str,
        language: CameroonLanguage = CameroonLanguage.FRENCH,
        speaker_wav: Optional[str] = None,
    ) -> Path:
        """Convert text to speech"""
        
        if not self._is_ready:
            raise TTSGenerationError("TTS model not loaded")
        
        logger.info("Synthesizing speech...")
        
        audio_id = uuid.uuid4()
        output_path = self.output_dir / f"{audio_id}.wav"
        
        lang_map = {
            CameroonLanguage.FRENCH: "fr",
            CameroonLanguage.ENGLISH: "en",
            CameroonLanguage.BAMEKA: "fr",
            CameroonLanguage.MEDUMBA: "fr",
            CameroonLanguage.YEMBA: "fr",
            CameroonLanguage.NGIEMBOON: "fr",
            CameroonLanguage.FEFE: "fr",
            CameroonLanguage.BAMILEKE: "fr",
            CameroonLanguage.PIDGIN: "en",
        }
        tts_lang = lang_map.get(language, "fr")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._synthesize_sync,
            text,
            str(output_path),
            tts_lang,
            speaker_wav,
        )
        
        return output_path
        
    def _synthesize_sync(
        self,
        text: str,
        output_path: str,
        language: str,
        speaker_wav: Optional[str],
    ) -> None:
        """Generate speech"""
        
        self.model.tts_to_file(
            text=text,
            file_path=output_path,
            language=language,
            speaker_wav=speaker_wav,
        )
    
    def is_ready(self) -> bool:
        return self._is_ready
        
    async def cleanup(self) -> None:
        """Cleanup"""
        if self.model:
            del self.model
                
        self._is_ready = False
        logger.info("TTS cleaned up")