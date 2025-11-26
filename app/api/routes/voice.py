"""Voice endpoints with audio response"""

import time
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    VoiceMessageRequest, 
    AssistantResponse, 
    ErrorResponse, 
    IntentInfo, 
    FlowInfo
)
from app.api.dependencies import (
    get_conversation_manager,
    get_stt_service,
    get_tts_service,
    get_audio_storage,
)
from app.core.conversation.manager import ConversationManager
from app.services.speech import STTService, TTSService
from app.storage import AudioStorageService
from app.utils.audio import download_audio
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
async def process_voice_message(
    request: VoiceMessageRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
    stt_service: STTService = Depends(get_stt_service),
    tts_service: TTSService = Depends(get_tts_service),
    audio_storage: AudioStorageService = Depends(get_audio_storage),
):
    start_time = time.time()
    
    try:
        logger.info(f"Processing voice message for user {request.user_id}")
        
        audio_data = await download_audio(str(request.audio_url))
        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail={
                    "errorCode": "AUDIO_DOWNLOAD_FAILED", 
                    "message": "Failed to download audio file"
                },
            )
        
        transcribed_text = await stt_service.transcribe(audio_data)
        if not transcribed_text:
            raise HTTPException(
                status_code=400,
                detail={
                    "errorCode": "TRANSCRIPTION_FAILED", 
                    "message": "Failed to transcribe audio"
                },
            )
        
        logger.info(f"Transcribed: {transcribed_text[:100]}...")

        # Language detection from user speech
        lang = detect_language(transcribed_text)
        
        response_text, metadata = await manager.process_message(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            phone_number=request.phone_number,
            text=transcribed_text,
        )

        # Ensure we always have a non-empty message
        if not isinstance(response_text, str) or not response_text.strip():
            logger.warning("ConversationManager returned empty/None response_text; using generic fallback.")
            response_text = build_generic_fallback(lang)
        
        audio_url = None
        audio_duration_ms = None
        
        if settings.TTS_ENABLED and response_text:
            try:
                response_audio = await tts_service.synthesize_to_bytes(
                    response_text,
                    voice_path=settings.TTS_VOICE_PATH,
                    format=settings.AUDIO_FORMAT,
                )
                
                if response_audio:
                    audio_url = await audio_storage.save_response_audio(
                        audio_data=response_audio,
                        conversation_id=request.conversation_id,
                        extension=settings.AUDIO_FORMAT,
                    )
                    audio_duration_ms = int(len(response_audio) / 24000 / 2 * 1000)
                    logger.info(f"Generated audio response: {audio_url}")
                    
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AssistantResponse(
            message=response_text,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            transcribed_text=transcribed_text,
            audio_url=audio_url,
            audio_duration_ms=audio_duration_ms,
            intent=IntentInfo(**metadata["intent"]) if metadata.get("intent") else None,
            flow=FlowInfo(**metadata["flow"]) if metadata.get("flow") else None,
            transaction_data=metadata.get("transaction_data"),
            processing_time_ms=processing_time,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"errorCode": "PROCESSING_ERROR", "message": str(e)},
        )