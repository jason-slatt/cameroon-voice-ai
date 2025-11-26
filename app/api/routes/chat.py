"""Chat (text) endpoints with optional audio response"""

import time
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    TextMessageRequest, 
    AssistantResponse, 
    ErrorResponse, 
    IntentInfo, 
    FlowInfo
)
from app.api.dependencies import (
    get_conversation_manager,
    get_tts_service,
    get_audio_storage,
)
from app.core.conversation.manager import ConversationManager
from app.services.speech import TTSService
from app.storage import AudioStorageService
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


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
    """
    Process a text message from the user.
    
    Optionally generates audio response if `includeAudio=true`.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing text message for user {request.user_id}: {request.text[:50]}...")

        # Process the message
        response_text, metadata = await manager.process_message(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            phone_number=request.phone_number,
            text=request.text,
        )

        if not isinstance(response_text, str) or not response_text.strip():
            logger.warning("ConversationManager returned empty/None response_text; sending fallback message.")
            response_text = "I'm not sure how to respond to that yet, but I'm here to help with your account, balance, withdrawals, and deposits."
        
        # Generate audio if requested
        audio_url = None
        audio_duration_ms = None
        
        if include_audio and settings.TTS_ENABLED and response_text:
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
                    
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AssistantResponse(
            message=response_text,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            audio_url=audio_url,
            audio_duration_ms=audio_duration_ms,
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