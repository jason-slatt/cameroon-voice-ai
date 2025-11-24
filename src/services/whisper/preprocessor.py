# src/services/whisper/preprocessor.py
"""
Audio preprocessing utilities
Handles download, format conversion, validation
"""
from pathlib import Path
from typing import Optional
import uuid

import librosa
import soundfile as sf

from src.core.exception import AudioProcessingError
from src.core.constants import SAMPLE_RATE, MAX_AUDIO_SIZE_MB, SUPPORTED_AUDIO_FORMATS
from src.core.logging import logger
from src.core.config import settings


class AudioPreprocessor:
    """
    Prepare audio files for Whisper
    
    Why preprocessing:
    - Whisper expects 16kHz sample rate
    - Mono audio (1 channel)
    - Normalized volume
    - Valid format
    """
    
    @staticmethod
    def validate_audio(audio_path: Path) -> None:
        """
        Validate audio file before processing
        
        Checks:
        - File exists
        - File size within limits
        - Format is supported
        """
        if not audio_path.exists():
            raise AudioProcessingError(f"File not found: {audio_path}")
        
        # Check file size
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_AUDIO_SIZE_MB:
            raise AudioProcessingError(
                f"File too large: {size_mb:.1f}MB (max: {MAX_AUDIO_SIZE_MB}MB)"
            )
        
        # Check format
        file_ext = audio_path.suffix.lower().lstrip('.')
        if file_ext not in SUPPORTED_AUDIO_FORMATS:
            raise AudioProcessingError(
                f"Unsupported format: {file_ext}. "
                f"Supported: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
            )
    
    @staticmethod
    async def preprocess(
        input_path: Path,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Preprocess audio file for Whisper
        
        Steps:
        1. Load audio
        2. Resample to 16kHz
        3. Convert to mono
        4. Normalize volume
        5. Save as WAV
        
        Args:
            input_path: Original audio file
            output_path: Where to save (optional, creates temp file if None)
            
        Returns:
            Path to preprocessed audio file
        """
        
        AudioPreprocessor.validate_audio(input_path)
        
        logger.info(f"Preprocessing audio: {input_path.name}")
        
        try:
            # Load audio with librosa (handles all formats)
            audio, sr = librosa.load(
                str(input_path),
                sr=SAMPLE_RATE,  # Resample to 16kHz
                mono=True,  # Convert to mono
            )
            
            # Normalize volume (avoid clipping)
            audio = librosa.util.normalize(audio)
            
            # Determine output path
            if output_path is None:
                # Create temp file
                output_dir = settings.AUDIO_STORAGE_PATH / "preprocessed"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{uuid.uuid4()}.wav"
            
            # Save as WAV (Whisper-friendly format)
            sf.write(
                str(output_path),
                audio,
                SAMPLE_RATE,
                format='WAV',
                subtype='PCM_16',  # 16-bit PCM
            )
            
            logger.info(f"Audio preprocessed: {output_path.name}")
            return output_path
            
        except Exception as e:
            raise AudioProcessingError(f"Preprocessing failed: {e}")
    
    @staticmethod
    def get_audio_duration(audio_path: Path) -> float:
        """Get audio duration in seconds"""
        try:
            duration = librosa.get_duration(path=str(audio_path))
            return duration
        except Exception as e:
            raise AudioProcessingError(f"Failed to get duration: {e}")