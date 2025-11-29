from __future__ import annotations
from typing import Optional
import os
import tempfile

from faster_whisper import WhisperModel

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
_whisper_model: Optional[WhisperModel] = None


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Whisper model: %s", settings.WHISPER_MODEL_NAME)
        _whisper_model = WhisperModel(
            settings.WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
        )
    return _whisper_model


def transcribe_audio(audio_bytes: bytes, language: Optional[str] = "en") -> str:
    """
    Transcribe raw audio bytes to text using Whisper base.en.
    """
    model = _get_whisper_model()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        temp_path = f.name

    try:
        segments, info = model.transcribe(temp_path, language=language)
        text = " ".join(segment.text for segment in segments).strip()
        logger.info("Transcription result: %s", text)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return text