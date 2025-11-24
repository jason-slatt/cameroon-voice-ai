# src/api/v1/endpoints/webhook.py
"""
WhatsApp webhook - receives messages from Botpress
"""
from fastapi import APIRouter, Request, BackgroundTasks
from pathlib import Path
import uuid

from src.core.dependencies import (
    get_whisper_service,
    get_llama_service,
    get_tts_service,
    get_botpress_client,
)
from src.core.logging import logger
from src.core.config import settings
from src.services.llama.memory import ConversationMemory
from src.services.whisper.preprocessor import AudioPreprocessor

router = APIRouter()


@router.post("/botpress")
async def botpress_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receives messages from Botpress/WhatsApp
    Processes and responds with language detection
    """
    
    try:
        data = await request.json()
        logger.info(f"📨 Webhook received: {data}")
        
        # Extract info
        event_type = data.get("type", "")
        
        if event_type != "message.created":
            return {"status": "ignored"}
        
        conversation_id = data.get("conversationId")
        payload = data.get("payload", {})
        message_type = payload.get("type", "text")
        
        if not conversation_id:
            return {"status": "no_conversation_id"}
        
        logger.info(f"📱 Message type: {message_type}")
        
        # ==================== TEXT MESSAGE ====================
        if message_type == "text":
            text = payload.get("text", "")
            
            if not text:
                return {"status": "empty_text"}
            
            logger.info(f"💬 Text: {text}")
            
            # Process in background
            background_tasks.add_task(
                process_text_message,
                conversation_id,
                text
            )
            
            return {"status": "processing_text"}
        
        # ==================== AUDIO MESSAGE ====================
        elif message_type in ["audio", "voice"]:
            audio_url = payload.get("audio")
            
            if not audio_url:
                return {"status": "no_audio_url"}
            
            logger.info(f"🎤 Audio message")
            
            # Process in background
            background_tasks.add_task(
                process_audio_message,
                conversation_id,
                audio_url
            )
            
            return {"status": "processing_audio"}
        
        else:
            logger.warning(f"Unsupported type: {message_type}")
            return {"status": "unsupported_type"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def process_text_message(conversation_id: str, text: str):
    """Process text message with language detection"""
    
    try:
        llama = get_llama_service()
        botpress = get_botpress_client()
        memory = ConversationMemory()
        
        # Get saved language or detect from text
        saved_language = await memory.get_language(conversation_id)
        
        # Save user message to history
        await memory.add_message(conversation_id, "user", text)
        
        # Generate response
        logger.info("🤖 Generating response...")
        response = await llama.generate_response(
            user_message=text,
            conversation_id=conversation_id,
            language=saved_language,
        )
        
        logger.info(f"✅ Response: {response}")
        
        # Save assistant message
        await memory.add_message(conversation_id, "assistant", response)
        
        # Send back to user
        await botpress.send_text(conversation_id, response)
        
    except Exception as e:
        logger.error(f"Error processing text: {e}", exc_info=True)
        
        # Send error message
        try:
            botpress = get_botpress_client()
            await botpress.send_text(
                conversation_id,
                "Sorry, I encountered an error. Please try again."
            )
        except:
            pass


async def process_audio_message(conversation_id: str, audio_url: str):
    """
    Process audio message:
    1. Download audio
    2. Transcribe with Whisper (detects language)
    3. Generate response with LLaMA
    4. Send text response (voice response later)
    """
    
    try:
        whisper = get_whisper_service()
        llama = get_llama_service()
        botpress = get_botpress_client()
        memory = ConversationMemory()
        
        # 1. Download audio
        logger.info("📥 Downloading audio...")
        audio_dir = settings.AUDIO_STORAGE_PATH / "downloads"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        audio_path = audio_dir / f"{uuid.uuid4()}.ogg"
        await botpress.download_audio(audio_url, str(audio_path))
        
        # 2. Preprocess
        logger.info("🔧 Preprocessing audio...")
        preprocessed_path = await AudioPreprocessor.preprocess(audio_path)
        
        # 3. Transcribe (DETECTS LANGUAGE)
        logger.info("🎙️ Transcribing...")
        text, detected_language, confidence = await whisper.transcribe(preprocessed_path)
        
        logger.info(f"📝 Transcription: {text}")
        logger.info(f"🌍 Language: {detected_language} (confidence: {confidence:.2%})")
        
        # Save detected language
        await memory.set_language(conversation_id, detected_language)
        
        # Save user message
        await memory.add_message(conversation_id, "user", text)
        
        # Send transcription confirmation
        await botpress.send_text(
            conversation_id,
            f"You said: {text}"
        )
        
        # 4. Generate response IN SAME LANGUAGE
        logger.info("🤖 Generating response...")
        response = await llama.generate_response(
            user_message=text,
            language=detected_language,  # Respond in detected language
            conversation_id=conversation_id,
        )
        
        logger.info(f"✅ Response: {response}")
        
        # Save assistant message
        await memory.add_message(conversation_id, "assistant", response)
        
        # 5. Send text response
        await botpress.send_text(conversation_id, response)
        
        logger.info("✅ Audio message processed successfully")
        
        # Cleanup
        audio_path.unlink(missing_ok=True)
        preprocessed_path.unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        
        try:
            botpress = get_botpress_client()
            await botpress.send_text(
                conversation_id,
                "Sorry, I couldn't process your voice message."
            )
        except:
            pass