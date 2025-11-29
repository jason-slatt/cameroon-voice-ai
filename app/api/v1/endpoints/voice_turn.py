from __future__ annotations
import base64
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.speech.stt_service import transcribe_audio
from app.services.speech.tts_service import synthesize_wav
from app.services.conversation.conversation_service import (
    get_or_create_state,
    handle_user_text,
)
from app.services.storage.storage_service import save_audio

router = APIRouter()


@router.post("/voice-turn", tags=["conversation"])
async def voice_turn(
    audio: UploadFile = File(..., description="User audio (e.g. WAV/OGG/MP3)"),
    session_id: Optional[str] = Form(default=None),
):
    """
    One voice turn:
      - STT: audio -> user_text
      - LLM + tools: user_text -> assistant_text
      - TTS: assistant_text -> audio
      - Store audio and return audio_id + base64 audio
    """
    if audio.content_type not in (
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/webm",
    ):
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {audio.content_type}")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # 1. STT
    user_text = transcribe_audio(audio_bytes)
    if not user_text:
        raise HTTPException(status_code=400, detail="Could not transcribe audio")

    # 2. Conversation
    state = await get_or_create_state(session_id)
    convo_result = await handle_user_text(state, user_text)
    assistant_text = convo_result["assistant_text"]
    session_id_out = convo_result["session_id"]

    # 3. TTS
    assistant_audio = synthesize_wav(assistant_text)

    # 4. Store audio
    audio_id = save_audio(session_id_out, assistant_audio, extension="wav")

    assistant_audio_b64 = base64.b64encode(assistant_audio).decode("ascii")

    return {
        "session_id": session_id_out,
        "user_text": user_text,
        "assistant_text": assistant_text,
        "assistant_audio_base64": assistant_audio_b64,
        "audio_format": "wav",
        "audio_id": audio_id,
    }