# app/api/routes/chat.py

import time
import re
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
    """Build generic fallback message in user's language"""
    if lang == "fr":
        return (
            "Je suis là pour vous aider avec votre compte BAFOKA : "
            "création de compte, consultation de compte, solde, retraits, dépôts, "
            "transferts, tableau de bord, gestion du mot de passe et liaison WhatsApp. "
            "Que souhaitez-vous faire ?"
        )
    else:
        return (
            "I'm here to help with your BAFOKA account: "
            "account creation, viewing your account, balance, withdrawals, deposits, "
            "transfers, dashboard, password management and WhatsApp linking. "
            "What would you like to do?"
        )


def sanitize_text_for_tts(text: str) -> str:
    """
    Sanitize text for TTS by removing markdown and special characters.
    TTS engines don't handle markdown well.
    """
    if not text:
        return text
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code`
    text = re.sub(r'```[\s\S]*?```', '', text)      # ```code blocks```
    
    # Remove bullet points
    text = re.sub(r'^[\•\-\*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    
    return text


@router.post(
    "/message",
    response_model=AssistantResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Process text message",
    description="Process a text message and return assistant response with optional audio",
)
async def process_text_message(
    request: TextMessageRequest,
    include_audio: bool = Query(
        False, 
        alias="includeAudio", 
        description="Include audio response (TTS)"
    ),
    manager: ConversationManager = Depends(get_conversation_manager),
    tts_service: TTSService = Depends(get_tts_service),
    audio_storage: AudioStorageService = Depends(get_audio_storage),
):
    """
    Process a text message from the user.
    
    Args:
        request: Text message request with user info and message text
        include_audio: If True, generate TTS audio response
        
    Returns:
        AssistantResponse with message text and optional audio URL
    """
    start_time = time.time()
    
    try:
        # Validate input
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "errorCode": "EMPTY_MESSAGE",
                    "message": "Message text cannot be empty"
                },
            )
        
        logger.info(
            f"Processing text message for user {request.user_id}, "
            f"conversation {request.conversation_id}: {request.text[:50]}..."
        )

        # Detect language
        lang = detect_language(request.text)
        logger.debug(f"Detected language: {lang}")

        # Process message through conversation manager
        response_text, metadata = await manager.process_message(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            phone_number=request.phone_number,
            text=request.text,
        )

        # Ensure we have a valid response
        if not isinstance(response_text, str) or not response_text.strip():
            logger.warning("ConversationManager returned empty/None response_text; using generic fallback.")
            response_text = build_generic_fallback(lang)

        logger.info(f"Response ({len(response_text)} chars): {response_text[:100]}...")

        # Generate TTS audio if requested
        audio_url = None
        audio_duration_ms = None
        
        if include_audio and settings.TTS_ENABLED and response_text:
            try:
                # Sanitize text for TTS
                tts_text = sanitize_text_for_tts(response_text)
                
                if tts_text:
                    response_audio = await tts_service.synthesize_to_bytes(
                        tts_text,
                        voice_path=settings.TTS_VOICE_PATH,
                        format=settings.AUDIO_FORMAT,
                    )
                    
                    if response_audio:
                        audio_url = await audio_storage.save_response_audio(
                            audio_data=response_audio,
                            conversation_id=request.conversation_id,
                            extension=settings.AUDIO_FORMAT,
                        )
                        # Calculate duration (assuming 24kHz, 16-bit mono)
                        audio_duration_ms = int(len(response_audio) / 24000 / 2 * 1000)
                        logger.info(f"Generated audio response: {audio_url} ({audio_duration_ms}ms)")
                    else:
                        logger.warning("TTS returned empty audio data")
                else:
                    logger.warning("Sanitized TTS text is empty, skipping TTS")
                    
            except Exception as e:
                logger.error(f"TTS generation failed: {e}", exc_info=True)
                # Continue without audio - text response is still valid

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Build response
        response = AssistantResponse(
            message=response_text,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            transcribed_text=request.text,  # For text input, this is the same as input
            audio_url=audio_url,
            audio_duration_ms=audio_duration_ms,
            intent=IntentInfo(**metadata["intent"]) if metadata.get("intent") else None,
            flow=FlowInfo(**metadata["flow"]) if metadata.get("flow") else None,
            transaction_data=metadata.get("transaction_data"),
            processing_time_ms=processing_time,
        )

        logger.info(
            f"Text message processed in {processing_time}ms | "
            f"Intent: {metadata.get('intent', {}).get('intent', 'N/A')} | "
            f"Flow: {metadata.get('flow', {}).get('flow_type', 'none')}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"errorCode": "PROCESSING_ERROR", "message": str(e)},
        )

