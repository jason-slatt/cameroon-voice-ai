# app/api/routes/chat.py

import time
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    TextMessageRequest,
    AssistantResponse,
    ErrorResponse,
    IntentInfo,
    FlowInfo,
)
from app.api.dependencies import get_conversation_manager, get_tts_service, get_audio_storage
from app.core.conversation.manager import ConversationManager
from app.services.speech import TTSService
from app.storage import AudioStorageService
from app.utils.lang import detect_language
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

def build_generic_fallback(lang: str) -> str:
    if lang == "fr":
        return (
            "Je suis là pour vous aider avec votre compte BAFOKA : "
            "création de compte, consultation de compte, solde, retraits et dépôts. "
            "Que souhaitez-vous faire ?"
        )
    else:
        return (
            "I'm here to help with your BAFOKA account: "
            "account creation, viewing your account, balance, withdrawals and deposits. "
            "What would you like to do?"
        )


@router.post(
    "/message",
    response_model=AssistantResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def process_text_message(
    request: TextMessageRequest,
    include_audio: bool = Query(False, alias="includeAudio", description="Include audio response"),
    manager: ConversationManager = Depends(get_conversation_manager),
    tts_service: TTSService = Depends(get_tts_service),
    audio_storage: AudioStorageService = Depends(get_audio_storage),
):
    start_time = time.time()
    try:
        logger.info(f"Processing text message for user {request.user_id}: {request.text[:50]}...")

        response_text, metadata = await manager.process_message(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            phone_number=request.phone_number,
            text=request.text,
        )

        lang = detect_language(request.text)

        if not isinstance(response_text, str) or not response_text.strip():
            logger.warning("ConversationManager returned empty/None response_text; using generic fallback.")
            response_text = build_generic_fallback(lang)

        # (Optional: generate TTS audio here if include_audio=True)

        processing_time = int((time.time() - start_time) * 1000)

        return AssistantResponse(
            message=response_text,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            audio_url=None,
            audio_duration_ms=None,
            intent=IntentInfo(**metadata["intent"]) if metadata.get("intent") else None,
            flow=FlowInfo(**metadata["flow"]) if metadata.get("flow") else None,
            transaction_data=metadata.get("transaction_data"),
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"errorCode": "PROCESSING_ERROR", "message": str(e)},
        )