"""Audio file serving endpoints"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

AUDIO_BASE_PATH = Path(settings.AUDIO_STORAGE_PATH)


@router.get("/{path:path}")
async def serve_audio(path: str):
    """
    Serve audio files.
    
    Args:
        path: Path to audio file relative to audio storage
    """
    file_path = AUDIO_BASE_PATH / path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Security: ensure path doesn't escape storage directory
    try:
        file_path.resolve().relative_to(AUDIO_BASE_PATH.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".webm": "audio/webm",
    }
    media_type = media_types.get(suffix, "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )