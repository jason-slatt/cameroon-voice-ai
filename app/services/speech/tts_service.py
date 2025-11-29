from __future__ annotations
from typing import Optional
import io

import numpy as np
import soundfile as sf
from TTS.api import TTS

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
_tts_model: Optional[TTS] = None


def _get_tts_model() -> TTS:
    global _tts_model
    if _tts_model is None:
        logger.info("Loading TTS model: %s", settings.TTS_MODEL_NAME)
        _tts_model = TTS(settings.TTS_MODEL_NAME)
    return _tts_model


def synthesize_wav(text: str) -> bytes:
    """
    Synthesize speech from text and return WAV bytes.
    """
    logger.info("Synthesizing TTS for text: %s", text)
    tts = _get_tts_model()
    audio = tts.tts(text=text)

    if not isinstance(audio, np.ndarray):
        audio = np.array(audio)

    buffer = io.BytesIO()
    sample_rate = getattr(tts, "output_sample_rate", None) or getattr(
        tts.synthesizer, "output_sample_rate", 22050
    )
    sf.write(buffer, audio, samplerate=sample_rate, format="WAV")
    return buffer.getvalue()