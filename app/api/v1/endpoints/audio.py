from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.storage.storage_service import get_audio_path

router = APIRouter()


@router.get("/audio/{audio_id}", tags=["audio"])
async def get_audio(audio_id: str):
    """
    Return stored audio for a given audio_id.
    """
    path = get_audio_path(audio_id, extension="wav")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(
        path,
        media_type="audio/wav",
        filename=path.name,
    )