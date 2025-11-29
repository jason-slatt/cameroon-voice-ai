from __future__ annotations
from pathlib import Path
from uuid import uuid4

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BASE_AUDIO_PATH = Path(settings.AUDIO_STORAGE_PATH)
BASE_AUDIO_PATH.mkdir(parents=True, exist_ok=True)


def save_audio(
    session_id: str,
    audio_bytes: bytes,
    extension: str = "wav",
) -> str:
    """
    Store generated audio on disk and return a generated audio_id.
    """
    audio_id = str(uuid4())
    filename = f"{audio_id}.{extension}"
    path = BASE_AUDIO_PATH / filename
    path.write_bytes(audio_bytes)
    logger.info(
        "Saved audio: session_id=%s audio_id=%s path=%s",
        session_id,
        audio_id,
        path,
    )
    return audio_id


def get_audio_path(audio_id: str, extension: str = "wav") -> Path:
    """
    Return path for a given audio_id.
    """
    return BASE_AUDIO_PATH / f"{audio_id}.{extension}"