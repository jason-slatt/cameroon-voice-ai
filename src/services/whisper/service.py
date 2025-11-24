# src/services/whisper/service.py
"""
Whisper Speech-to-Text Service
Converts audio files to text transcriptions
"""
import asyncio
from pathlib import Path
from typing import Optional, Tuple
import time

import torch
import whisper
from whisper import Whisper

from src.core.exception import TranscriptionError
from src.core.config import settings
from src.core.constants import CameroonLanguage
from src.core.logging import logger
import torch



class WhisperService:
    """
    Whisper STT Service
    
    Why Whisper:
    - Works with 99 languages out of the box
    - Includes French (common in Cameroon)
    - Can detect language automatically
    - Very accurate, fast inference
    
    For prototype: Use 'base' model (good balance of speed/accuracy)
    Later: Fine-tune on your Cameroon languages
    """
    
    def __init__(self):
        self.model: Optional[Whisper] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._is_ready = False
            
    async def initialize(self) -> None:
        """
        Load Whisper model
        Called once on application startup
        """
        if self._is_ready:
            return
            
        logger.info("Loading Whisper model...")
        start_time = time.time()
        
        # Load model in thread pool (CPU/GPU intensive)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_sync)
        
        load_time = time.time() - start_time
        logger.info(f"✅ Whisper loaded in {load_time:.2f}s")
        self._is_ready = True
        
    def _load_model_sync(self) -> None:
        """
        Actually load the model (runs in background thread)
        
        Model sizes:
        - tiny: 39M params, ~1GB RAM, fastest
        - base: 74M params, ~1.5GB RAM, good balance ✅ USE THIS
        - small: 244M params, ~2GB RAM, more accurate
        - medium: 769M params, ~5GB RAM, very accurate
        - large: 1550M params, ~10GB RAM, best accuracy
        """
        model_size = "base"  # Start with base for prototype
        
        self.model = whisper.load_model(
            model_size,
            device=self.device,
            download_root=str(Path("./models")),  # Save models here
        )
        
        logger.info(f"Whisper '{model_size}' loaded on {self.device}")
        
    async def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[CameroonLanguage] = None,
    ) -> Tuple[str, CameroonLanguage, float]:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file (WAV, MP3, OGG, etc.)
            language: Force specific language (optional)
            
        Returns:
            (transcription_text, detected_language, confidence_score)
            
        Example:
            text, lang, conf = await whisper.transcribe("audio.mp3")
            # "Bonjour, comment allez-vous?", CameroonLanguage.FRENCH, 0.95
        """
        if not self._is_ready:
            raise TranscriptionError("Whisper model not loaded")
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing: {audio_path.name}")
        start_time = time.time()
        
        # Run transcription in thread pool (blocking operation)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            str(audio_path),
            language,
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"Transcription completed in {processing_time:.2f}s: "
            f"'{result[0][:50]}...'"
        )
        
        return result
        
    def _transcribe_sync(
        self,
        audio_path: str,
        language: Optional[CameroonLanguage],
    ) -> Tuple[str, CameroonLanguage, float]:
        """
        Actually transcribe (runs in background thread)
        """
        
        # Map our language enum to Whisper's language codes
        language_map = {
            CameroonLanguage.FRENCH: "fr",
            CameroonLanguage.ENGLISH: "en",
            # For local languages, use French for now
            # (we'll fine-tune later to recognize them)
            CameroonLanguage.BAMEKA: "fr",
            CameroonLanguage.MEDUMBA: "fr",
            CameroonLanguage.YEMBA: "fr",
            CameroonLanguage.NGIEMBOON: "fr",
            CameroonLanguage.FEFE: "fr",
            CameroonLanguage.BAMILEKE: "fr",
            CameroonLanguage.PIDGIN: "en",  # Treat pidgin as English
        }
        
        # Prepare transcription options
        options = {
            "fp16": torch.cuda.is_available(),  # Use FP16 on GPU for speed
            "task": "transcribe",  # vs 'translate' (we want original language)
            "verbose": False,
        }
        
        # Set language if specified
        if language:
            options["language"] = language_map.get(language, "fr")
        
        # Transcribe
        result = self.model.transcribe(audio_path, **options)
        
        # Extract results
        text = result["text"].strip()
        detected_lang_code = result.get("language", "fr")
        
        # Map back to our language enum
        reverse_map = {
            "fr": CameroonLanguage.FRENCH,
            "en": CameroonLanguage.ENGLISH,
        }
        detected_language = reverse_map.get(
            detected_lang_code,
            CameroonLanguage.FRENCH
        )
        
        # Calculate confidence from segments
        # Whisper gives per-segment probabilities
        segments = result.get("segments", [])
        if segments:
            # Average confidence across all segments
            confidences = []
            for seg in segments:
                # no_speech_prob = probability it's NOT speech
                # confidence = 1 - no_speech_prob
                no_speech = seg.get("no_speech_prob", 0.0)
                confidences.append(1.0 - no_speech)
            
            confidence = sum(confidences) / len(confidences)
        else:
            confidence = 0.95  # Default high confidence
        
        return text, detected_language, confidence
    
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self._is_ready
        
    async def cleanup(self) -> None:
        """Clean up resources on shutdown"""
        if self.model:
            del self.model
            self.model = None
            
            # Clear GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        self._is_ready = False
        logger.info("Whisper service cleaned up")