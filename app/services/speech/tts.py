"""Text-to-Speech service using ChatterBox"""

import torch
import numpy as np
import nltk
import warnings
import io
import soundfile as sf
from typing import Optional, Tuple
from functools import lru_cache

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Suppress warnings
warnings.filterwarnings(
    "ignore",
    message="torch.nn.utils.weight_norm is deprecated",
)

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


class TTSService:
    """Text-to-Speech service using ChatterBox TTS"""
    
    def __init__(self):
        self.model = None
        self.sample_rate = 24000  # ChatterBox default
        self._loaded = False
        self._device = None
    
    def _get_device(self) -> str:
        """Determine the best device to use"""
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            logger.info(f"TTS using device: {self._device}")
        return self._device
    
    def _ensure_loaded(self):
        """Lazy load the model"""
        if not self._loaded:
            logger.info("Loading ChatterBox TTS model...")
            
            # Patch torch.load for device compatibility
            device = self._get_device()
            if not hasattr(torch, '_original_load'):
                torch._original_load = torch.load
                
                def patched_load(*args, **kwargs):
                    if 'map_location' not in kwargs:
                        kwargs['map_location'] = torch.device(device)
                    return torch._original_load(*args, **kwargs)
                
                torch.load = patched_load
            
            from chatterbox.tts import ChatterboxTTS
            self.model = ChatterboxTTS.from_pretrained(device=device)
            self.sample_rate = self.model.sr
            self._loaded = True
            logger.info(f"ChatterBox TTS loaded. Sample rate: {self.sample_rate}")
    
    async def synthesize(
        self,
        text: str,
        voice_path: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> Tuple[int, np.ndarray]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_path: Optional path to voice sample for cloning
            exaggeration: Emotion exaggeration (0-1)
            cfg_weight: CFG weight for pacing (0-1)
            
        Returns:
            Tuple of (sample_rate, audio_array)
        """
        self._ensure_loaded()
        
        if not text or not text.strip():
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        try:
            wav = self.model.generate(
                text,
                audio_prompt_path=voice_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
            
            audio_array = wav.squeeze().cpu().numpy()
            return self.sample_rate, audio_array
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
    
    async def synthesize_long_form(
        self,
        text: str,
        voice_path: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> Tuple[int, np.ndarray]:
        """
        Synthesize long-form text with sentence-by-sentence processing.
        
        Args:
            text: Text to synthesize
            voice_path: Optional path to voice sample for cloning
            exaggeration: Emotion exaggeration (0-1)
            cfg_weight: CFG weight for pacing (0-1)
            
        Returns:
            Tuple of (sample_rate, audio_array)
        """
        self._ensure_loaded()
        
        if not text or not text.strip():
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        try:
            pieces = []
            sentences = nltk.sent_tokenize(text)
            silence = np.zeros(int(0.2 * self.sample_rate))  # 200ms pause
            
            for i, sent in enumerate(sentences):
                sent = sent.strip()
                if not sent:
                    continue
                
                _, audio = await self.synthesize(
                    sent,
                    voice_path=voice_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                )
                pieces.append(audio)
                
                if i < len(sentences) - 1:
                    pieces.append(silence.copy())
            
            if not pieces:
                return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
            
            return self.sample_rate, np.concatenate(pieces)
            
        except Exception as e:
            logger.error(f"TTS long-form synthesis error: {e}")
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
    
    async def synthesize_to_bytes(
        self,
        text: str,
        voice_path: Optional[str] = None,
        format: str = "wav",
    ) -> Optional[bytes]:
        """
        Synthesize speech and return as bytes.
        
        Args:
            text: Text to synthesize
            voice_path: Optional path to voice sample
            format: Audio format (wav, mp3, ogg)
            
        Returns:
            Audio bytes or None if failed
        """
        sample_rate, audio = await self.synthesize_long_form(
            text,
            voice_path=voice_path,
        )
        
        if audio.size == 0:
            return None
        
        try:
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format=format)
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            logger.error(f"Error converting audio to bytes: {e}")
            return None


@lru_cache()
def get_tts_service() -> TTSService:
    """Get cached TTS service instance"""
    return TTSService()