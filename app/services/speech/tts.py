"""Text-to-Speech service with ChatterBox and Edge-TTS fallback"""

import torch
import numpy as np
import nltk
import warnings
import io
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple
from functools import lru_cache
from enum import Enum

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Suppress warnings
warnings.filterwarnings(
    "ignore",
    message="torch.nn.utils.weight_norm is deprecated",
)


def _ensure_nltk_data():
    """Download required NLTK data"""
    for resource in ['punkt', 'punkt_tab']:
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            try:
                nltk.download(resource, quiet=True)
            except Exception:
                pass


_ensure_nltk_data()


class TTSEngine(Enum):
    """Available TTS engines"""
    CHATTERBOX = "chatterbox"
    EDGE_TTS = "edge_tts"
    AUTO = "auto"  # Use ChatterBox if available, else Edge-TTS


class EdgeTTSWrapper:
    """Wrapper for Edge-TTS (Microsoft's free TTS API)"""
    
    # Voice mapping for different languages
    VOICES = {
        'en': 'en-US-AriaNeural',
        'en-us': 'en-US-AriaNeural',
        'en-gb': 'en-GB-SoniaNeural',
        'fr': 'fr-FR-DeniseNeural',
        'fr-fr': 'fr-FR-DeniseNeural',
        'fr-ca': 'fr-CA-SylvieNeural',
        # Cameroonian French - use standard French voice
        'fr-cm': 'fr-FR-DeniseNeural',
    }
    
    def __init__(self):
        self.sample_rate = 24000  # Edge-TTS default
        self._available = None
    
    async def is_available(self) -> bool:
        """Check if edge-tts is available"""
        if self._available is None:
            try:
                import edge_tts
                self._available = True
            except ImportError:
                self._available = False
                logger.warning("edge-tts not installed. Install with: pip install edge-tts")
        return self._available
    
    def get_voice(self, language: str = 'en') -> str:
        """Get the appropriate voice for a language"""
        lang = language.lower().strip()
        return self.VOICES.get(lang, self.VOICES.get(lang.split('-')[0], self.VOICES['en']))
    
    async def synthesize(
        self,
        text: str,
        language: str = 'en',
        voice: Optional[str] = None,
    ) -> Tuple[int, np.ndarray]:
        """
        Synthesize speech using Edge-TTS.
        
        Args:
            text: Text to synthesize
            language: Language code
            voice: Optional specific voice name
            
        Returns:
            Tuple of (sample_rate, audio_array)
        """
        if not await self.is_available():
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        if not text or not text.strip():
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        try:
            import edge_tts
            import soundfile as sf
            
            voice_name = voice or self.get_voice(language)
            
            # Create communicate object
            communicate = edge_tts.Communicate(text, voice_name)
            
            # Use temp file for audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                # Save to temp file
                await communicate.save(tmp_path)
                
                # Read audio file
                audio_data, sample_rate = sf.read(tmp_path)
                
                # Convert to mono if stereo
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(axis=1)
                
                self.sample_rate = sample_rate
                return sample_rate, audio_data.astype(np.float32)
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}")
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
    
    async def synthesize_to_bytes(
        self,
        text: str,
        language: str = 'en',
        voice: Optional[str] = None,
        format: str = 'mp3',
    ) -> Optional[bytes]:
        """
        Synthesize speech and return as bytes (more efficient for Edge-TTS).
        
        Args:
            text: Text to synthesize
            language: Language code
            voice: Optional specific voice name
            format: Output format (mp3 is native for edge-tts)
            
        Returns:
            Audio bytes or None if failed
        """
        if not await self.is_available():
            return None
        
        if not text or not text.strip():
            return None
        
        try:
            import edge_tts
            
            voice_name = voice or self.get_voice(language)
            communicate = edge_tts.Communicate(text, voice_name)
            
            # Collect audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            if audio_chunks:
                audio_bytes = b"".join(audio_chunks)
                
                # If different format requested, convert
                if format != 'mp3':
                    audio_bytes = await self._convert_format(audio_bytes, format)
                
                return audio_bytes
            
            return None
            
        except Exception as e:
            logger.error(f"Edge-TTS synthesis to bytes error: {e}")
            return None
    
    async def _convert_format(self, mp3_bytes: bytes, target_format: str) -> bytes:
        """Convert MP3 bytes to another format"""
        try:
            import soundfile as sf
            
            # Read MP3 from bytes
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_in:
                tmp_in.write(mp3_bytes)
                tmp_in_path = tmp_in.name
            
            try:
                audio_data, sample_rate = sf.read(tmp_in_path)
                
                # Write to target format
                buffer = io.BytesIO()
                sf.write(buffer, audio_data, sample_rate, format=target_format)
                buffer.seek(0)
                return buffer.read()
            finally:
                os.unlink(tmp_in_path)
                
        except Exception as e:
            logger.warning(f"Format conversion failed, returning MP3: {e}")
            return mp3_bytes


class ChatterBoxWrapper:
    """Wrapper for ChatterBox TTS"""
    
    def __init__(self):
        self.model = None
        self.sample_rate = 24000
        self._loaded = False
        self._loading = False
        self._device = None
        self._load_error = None
        self._load_lock = asyncio.Lock()
    
    def _get_device(self) -> str:
        """Determine the best device to use"""
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            logger.info(f"ChatterBox TTS using device: {self._device}")
        return self._device
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._loaded
    
    def is_loading(self) -> bool:
        """Check if model is currently loading"""
        return self._loading
    
    async def is_available(self) -> bool:
        """Check if ChatterBox is available (loaded or can be loaded)"""
        if self._loaded:
            return True
        if self._load_error:
            return False
        
        # Check if chatterbox is installed
        try:
            import chatterbox
            return True
        except ImportError:
            return False
    
    async def load(self, timeout: float = 300.0) -> bool:
        """
        Load the ChatterBox model.
        
        Args:
            timeout: Maximum time to wait for loading (seconds)
            
        Returns:
            True if loaded successfully
        """
        if self._loaded:
            return True
        
        if self._load_error:
            return False
        
        async with self._load_lock:
            if self._loaded:
                return True
            
            if self._loading:
                # Wait for loading to complete
                start = asyncio.get_event_loop().time()
                while self._loading and (asyncio.get_event_loop().time() - start) < timeout:
                    await asyncio.sleep(0.5)
                return self._loaded
            
            self._loading = True
            
            try:
                logger.info("Loading ChatterBox TTS model...")
                
                # Run in executor to not block
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, self._load_sync),
                    timeout=timeout
                )
                
                self._loaded = True
                logger.info(f"ChatterBox TTS loaded. Sample rate: {self.sample_rate}")
                return True
                
            except asyncio.TimeoutError:
                self._load_error = "Model loading timed out"
                logger.error(f"ChatterBox loading timed out after {timeout}s")
                return False
            except Exception as e:
                self._load_error = str(e)
                logger.error(f"Failed to load ChatterBox: {e}")
                return False
            finally:
                self._loading = False
    
    def _load_sync(self):
        """Synchronous model loading"""
        device = self._get_device()
        
        # Patch torch.load for device compatibility
        if not hasattr(torch, '_original_load'):
            torch._original_load = torch.load
            
            def patched_load(*args, **kwargs):
                if 'map_location' not in kwargs:
                    kwargs['map_location'] = torch.device(device)
                if 'weights_only' not in kwargs:
                    kwargs['weights_only'] = False
                return torch._original_load(*args, **kwargs)
            
            torch.load = patched_load
        
        from chatterbox.tts import ChatterboxTTS
        self.model = ChatterboxTTS.from_pretrained(device=device)
        self.sample_rate = self.model.sr
    
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
        if not self._loaded:
            if not await self.load():
                return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        if not text or not text.strip():
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        try:
            # Run generation in executor
            loop = asyncio.get_event_loop()
            wav = await loop.run_in_executor(
                None,
                lambda: self.model.generate(
                    text,
                    audio_prompt_path=voice_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                )
            )
            
            audio_array = wav.squeeze().cpu().numpy()
            return self.sample_rate, audio_array
            
        except Exception as e:
            logger.error(f"ChatterBox synthesis error: {e}")
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))


class TTSService:
    """Text-to-Speech service with multiple engine support"""
    
    def __init__(self, engine: TTSEngine = TTSEngine.AUTO):
        self.engine_preference = engine
        self._chatterbox = ChatterBoxWrapper()
        self._edge_tts = EdgeTTSWrapper()
        self._current_engine: Optional[str] = None
    
    @property
    def sample_rate(self) -> int:
        """Get current sample rate"""
        if self._current_engine == "chatterbox" and self._chatterbox.is_loaded():
            return self._chatterbox.sample_rate
        return self._edge_tts.sample_rate
    
    async def initialize(self, preload_chatterbox: bool = False, timeout: float = 300.0):
        """
        Initialize TTS service.
        
        Args:
            preload_chatterbox: Whether to preload ChatterBox model
            timeout: Timeout for model loading
        """
        if preload_chatterbox and self.engine_preference in [TTSEngine.CHATTERBOX, TTSEngine.AUTO]:
            logger.info("Pre-loading ChatterBox model...")
            success = await self._chatterbox.load(timeout=timeout)
            if success:
                self._current_engine = "chatterbox"
                logger.info("ChatterBox pre-loaded successfully")
            else:
                logger.warning("ChatterBox pre-load failed, will use Edge-TTS")
                self._current_engine = "edge_tts"
    
    async def _get_engine(self) -> Tuple[str, object]:
        """Get the appropriate TTS engine based on preference and availability"""
        if self.engine_preference == TTSEngine.CHATTERBOX:
            if self._chatterbox.is_loaded() or await self._chatterbox.is_available():
                return "chatterbox", self._chatterbox
            logger.warning("ChatterBox not available, falling back to Edge-TTS")
            return "edge_tts", self._edge_tts
        
        elif self.engine_preference == TTSEngine.EDGE_TTS:
            return "edge_tts", self._edge_tts
        
        else:  # AUTO
            # Prefer ChatterBox if already loaded
            if self._chatterbox.is_loaded():
                return "chatterbox", self._chatterbox
            # Otherwise use Edge-TTS for speed
            if await self._edge_tts.is_available():
                return "edge_tts", self._edge_tts
            # Fall back to ChatterBox
            return "chatterbox", self._chatterbox
    
    async def synthesize(
        self,
        text: str,
        voice_path: Optional[str] = None,
        language: str = 'en',
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> Tuple[int, np.ndarray]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_path: Optional path to voice sample (ChatterBox only)
            language: Language code (Edge-TTS only)
            exaggeration: Emotion exaggeration (ChatterBox only)
            cfg_weight: CFG weight (ChatterBox only)
            
        Returns:
            Tuple of (sample_rate, audio_array)
        """
        engine_name, engine = await self._get_engine()
        self._current_engine = engine_name
        
        if engine_name == "chatterbox":
            return await engine.synthesize(
                text,
                voice_path=voice_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
        else:
            return await engine.synthesize(text, language=language)
    
    async def synthesize_long_form(
        self,
        text: str,
        voice_path: Optional[str] = None,
        language: str = 'en',
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> Tuple[int, np.ndarray]:
        """
        Synthesize long-form text with sentence-by-sentence processing.
        
        Args:
            text: Text to synthesize
            voice_path: Optional path to voice sample
            language: Language code
            exaggeration: Emotion exaggeration
            cfg_weight: CFG weight
            
        Returns:
            Tuple of (sample_rate, audio_array)
        """
        if not text or not text.strip():
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
        
        engine_name, engine = await self._get_engine()
        self._current_engine = engine_name
        
        # Edge-TTS handles long text well, so process as single call
        if engine_name == "edge_tts":
            return await engine.synthesize(text, language=language)
        
        # ChatterBox - process sentence by sentence
        try:
            pieces = []
            sentences = nltk.sent_tokenize(text)
            sample_rate = self.sample_rate
            silence = np.zeros(int(0.2 * sample_rate))  # 200ms pause
            
            for i, sent in enumerate(sentences):
                sent = sent.strip()
                if not sent:
                    continue
                
                sr, audio = await engine.synthesize(
                    sent,
                    voice_path=voice_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                )
                sample_rate = sr
                pieces.append(audio)
                
                if i < len(sentences) - 1:
                    pieces.append(silence.copy())
            
            if not pieces:
                return sample_rate, np.zeros(int(0.1 * sample_rate))
            
            return sample_rate, np.concatenate(pieces)
            
        except Exception as e:
            logger.error(f"TTS long-form synthesis error: {e}")
            return self.sample_rate, np.zeros(int(0.1 * self.sample_rate))
    
    async def synthesize_to_bytes(
        self,
        text: str,
        voice_path: Optional[str] = None,
        language: str = 'en',
        format: str = "wav",
    ) -> Optional[bytes]:
        """
        Synthesize speech and return as bytes.
        
        Args:
            text: Text to synthesize
            voice_path: Optional path to voice sample
            language: Language code
            format: Audio format (wav, mp3, ogg)
            
        Returns:
            Audio bytes or None if failed
        """
        engine_name, engine = await self._get_engine()
        self._current_engine = engine_name
        
        # Edge-TTS has native byte output
        if engine_name == "edge_tts":
            result = await engine.synthesize_to_bytes(
                text, 
                language=language, 
                format=format
            )
            if result:
                return result
        
        # ChatterBox or Edge-TTS fallback
        sample_rate, audio = await self.synthesize_long_form(
            text,
            voice_path=voice_path,
            language=language,
        )
        
        if audio.size == 0:
            return None
        
        try:
            import soundfile as sf
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format=format)
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            logger.error(f"Error converting audio to bytes: {e}")
            return None
    
    def get_status(self) -> dict:
        """Get TTS service status"""
        return {
            "engine_preference": self.engine_preference.value,
            "current_engine": self._current_engine,
            "chatterbox_loaded": self._chatterbox.is_loaded(),
            "chatterbox_loading": self._chatterbox.is_loading(),
            "chatterbox_error": self._chatterbox._load_error,
            "sample_rate": self.sample_rate,
        }


# Global service instance
_tts_service: Optional[TTSService] = None


def get_tts_service(engine: TTSEngine = TTSEngine.AUTO) -> TTSService:
    """Get TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService(engine=engine)
    return _tts_service


async def initialize_tts(preload_chatterbox: bool = False):
    """Initialize TTS service on startup"""
    service = get_tts_service()
    await service.initialize(preload_chatterbox=preload_chatterbox)
    return service