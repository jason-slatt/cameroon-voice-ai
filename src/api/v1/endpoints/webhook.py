# src/api/v1/endpoints/webhook.py
"""
WhatsApp webhook - receives messages from Botpress
NOW WITH NLU: Intent Classification + Entity Extraction
"""
from pathlib import Path
import uuid

from fastapi import (
    APIRouter,
    Request,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from src.core.constants import MAX_AUDIO_DURATION_SECONDS, CameroonLanguage
from src.services.banking.orchestrator import BankingOrchestrator
from src.services.text_processing.cleaner import BankingTextCleaner
from src.services.tts.service import TTSService
from src.core.config import settings
from src.core.dependencies import (
    get_banking_orchestrator,
    get_whisper_service,
    get_botpress_client,
    get_intent_classifier,
    get_entity_extractor,
)
from src.core.logging import logger
from src.services.llama.memory import ConversationMemory
from src.services.whisper.preprocessor import AudioPreprocessor

router = APIRouter()


@router.get("/botpress")
async def botpress_webhook_get(
    conversationId: str | None = None,
    text: str | None = None,
):
    """
    GET endpoint for text messages
    Now processes with NLU and banking logic
    """

    logger.info("📨 GET - ConvID: %s, Text: %s", conversationId, text)

    if not text:
        return {"response": "No text provided"}

    try:
        text_cleaner = BankingTextCleaner()
        intent_classifier = get_intent_classifier()
        entity_extractor = get_entity_extractor()
        banking_orchestrator = get_banking_orchestrator()
        memory = ConversationMemory()

        if not intent_classifier.is_ready():
            await intent_classifier.initialize()

        cleaned_text = text_cleaner.clean(text)
        logger.info("🧹 Cleaned: %s", cleaned_text)

        intent, confidence = intent_classifier.classify(cleaned_text)
        logger.info("🎯 Intent: %s (confidence: %.2f)", intent, confidence)

        entities = entity_extractor.extract(cleaned_text)
        logger.info("📦 Entities: %s", entities)

        is_valid, missing = entity_extractor.validate_entities(intent, entities)

        if not is_valid:
            missing_str = ", ".join(missing)
            return {
                "response": f"Pour continuer, j'ai besoin de: {missing_str}",
                "intent": intent,
                "missing_entities": missing,
            }

        result = await banking_orchestrator.process_command(
            intent=intent,
            entities=entities,
            conversation_id=conversationId or "default",
            user_id=conversationId or "default",  # TODO: real user_id
        )

        if conversationId:
            await memory.add_message(conversationId, "user", text)
            await memory.add_message(conversationId, "assistant", result["response"])

        logger.info("✅ Banking response: %s", result["response"])

        return {
            "response": result["response"],
            "intent": intent,
            "entities": entities,
            "status": result.get("status", "success"),
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("Error in GET /botpress: %s", exc, exc_info=True)
        return {
            "response": "Désolé, une erreur s'est produite. Veuillez réessayer.",
            "error": str(exc),
        }


@router.post("/botpress")
async def botpress_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    POST endpoint for Botpress webhooks
    Handles both text and audio messages
    """

    try:
        data = await request.json()
        logger.info("📨 Webhook received: %s", data)

        event_type = data.get("type", "")

        if event_type != "message.created":
            return {"status": "ignored"}

        conversation_id = data.get("conversationId")
        payload = data.get("payload", {})
        message_type = payload.get("type", "text")

        if not conversation_id:
            return {"status": "no_conversation_id"}

        logger.info("📱 Message type: %s", message_type)

        if message_type == "text":
            text = payload.get("text", "")

            if not text:
                return {"status": "empty_text"}

            logger.info("💬 Text: %s", text)

            background_tasks.add_task(
                process_text_with_nlu,
                conversation_id,
                text,
            )

            return {"status": "processing_text"}

        if message_type in {"audio", "voice"}:
            audio_url = payload.get("audio")

            if not audio_url:
                return {"status": "no_audio_url"}

            logger.info("🎤 Audio message")

            background_tasks.add_task(
                process_audio_with_nlu,
                conversation_id,
                audio_url,
            )

            return {"status": "processing_audio"}

        logger.warning("Unsupported type: %s", message_type)
        return {"status": "unsupported_type"}

    except Exception as exc:  # noqa: BLE001
        logger.error("Webhook error: %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}
from pathlib import Path
import uuid

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from src.core.config import settings
from src.core.logging import logger
from src.core.constants import CameroonLanguage
from src.services.whisper.preprocessor import AudioPreprocessor
from src.core.dependencies import (
    get_whisper_service,
    get_intent_classifier,
    get_entity_extractor,
)
from src.services.banking.orchestrator import BankingOrchestrator
from src.services.llama.memory import ConversationMemory
from src.services.text_processing.cleaner import BankingTextCleaner

router = APIRouter()

# ====== Safety thresholds (no magic numbers) ======
STT_CONFIDENCE_MIN = 0.85
INTENT_CONFIDENCE_MIN = 0.80

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from src.core.config import settings
from src.core.logging import logger
from src.core.constants import CameroonLanguage
from src.services.whisper.preprocessor import AudioPreprocessor
from src.core.dependencies import (
    get_whisper_service,
    get_intent_classifier,
    get_entity_extractor,
)
from src.services.banking.orchestrator import BankingOrchestrator
from src.services.llama.memory import ConversationMemory
from src.services.text_processing.cleaner import BankingTextCleaner

import re
from pathlib import Path
import uuid

router = APIRouter()


def _is_text_valid_for_french_banking(text: str, stt_conf: float) -> bool:
    """
    Heuristic to reject obviously bad STT output.

    Rules:
    - Minimum confidence (e.g. 0.75)
    - At least 3 alphabetic characters
    - At least 2 "real" words (length >= 2)
    - Mostly Latin letters (avoid cases like 'd 질문')
    """

    # 1) Confidence gate
    if stt_conf < 0.75:
        return False

    # 2) Extract only latin letters + French accents + spaces
    latin_only = re.sub(r"[^a-zàâäéèêëïîôöùûüç\s]", "", text.lower())
    # Count alphabetic characters
    alpha_chars = re.sub(r"[^a-zàâäéèêëïîôöùûüç]", "", latin_only)

    if len(alpha_chars) < 3:
        # Too short / too little actual text
        return False

    # 3) Count "real" words (length >= 2)
    tokens = [t for t in latin_only.split() if len(t) >= 2]
    if len(tokens) < 2:
        return False

    return True


# Threshold to consider STT reliable enough
MIN_STT_CONFIDENCE: float = 0.70


@router.post("/dev-voice-test")
async def dev_voice_test(
    conversation_id: str = Form("dev-local"),
    audio: UploadFile = File(...),
):
    """
    Dev endpoint to test the full voice → NLU → banking pipeline with a local file.

    - Accepts an uploaded audio file (WhatsApp .ogg, .mp3, .wav, etc.)
    - Runs:
        Whisper → text cleaning → intent classification → entity extraction
        → banking orchestrator
    - Returns everything in JSON (no Botpress involved)
    """

    try:
        # ====== 1. Save uploaded file ======
        audio_dir = settings.AUDIO_STORAGE_PATH / "dev_uploads"
        audio_dir.mkdir(parents=True, exist_ok=True)

        from pathlib import Path
        import uuid

        ext = Path(audio.filename).suffix or ".ogg"
        raw_path = audio_dir / f"{uuid.uuid4()}{ext}"

        data = await audio.read()
        with open(raw_path, "wb") as f:
            f.write(data)

        logger.info(f"🎧 Dev voice test file saved: {raw_path}")

        # ====== 2. Get services ======
        whisper = get_whisper_service()
        intent_classifier = get_intent_classifier()
        entity_extractor = get_entity_extractor()
        banking_orchestrator = BankingOrchestrator()
        memory = ConversationMemory()
        text_cleaner = BankingTextCleaner()

        # ====== 3. Preprocess audio ======
        preprocessed_path = await AudioPreprocessor.preprocess(raw_path)

        # ====== 4. Transcribe with Whisper ======
        transcription, detected_language, stt_conf = await whisper.transcribe(
            preprocessed_path,
            language=CameroonLanguage.FRENCH,  # we focus on FR for now
        )
        logger.info(
            f"📝 Dev transcription: {transcription} "
            f"(lang={detected_language}, conf={stt_conf:.2f})"
        )

        # Save language to memory (optional)
        await memory.set_language(conversation_id, detected_language)

        # ====== 4.b STT confidence gate ======
        if stt_conf < MIN_STT_CONFIDENCE:
            # Don't trust this text as a banking command
            return {
                "mode": "dev-voice-test",
                "conversation_id": conversation_id,
                "transcription": transcription,
                "detected_language": str(detected_language),
                "stt_confidence": stt_conf,
                "cleaned_text": transcription,  # not really relevant here
                "intent": None,
                "intent_confidence": 0.0,
                "entities": {},
                "status": "low_stt_confidence",
                "response": (
                    "Je ne suis pas sûr d'avoir bien compris. "
                    "Peux-tu répéter plus clairement, par exemple : "
                    "\"je veux envoyer 10 000 francs à Paul\" ?"
                ),
            }

        # ====== 5. NLU: clean + intent + entities ======
        cleaned = text_cleaner.clean(transcription)
        intent, intent_conf = intent_classifier.classify(cleaned)
        entities = entity_extractor.extract(cleaned)

        # ====== 5.a No clear banking intent ======
        if intent is None:
            return {
                "mode": "dev-voice-test",
                "conversation_id": conversation_id,
                "transcription": transcription,
                "detected_language": str(detected_language),
                "stt_confidence": stt_conf,
                "cleaned_text": cleaned,
                "intent": None,
                "intent_confidence": intent_conf,
                "entities": entities,
                "status": "no_intent",
                "response": (
                    "Je n'ai pas reconnu une demande bancaire claire. "
                    "Peux-tu reformuler, par exemple : "
                    "\"je veux envoyer 10 000 francs à Paul\" "
                    "ou \"paye une facture Orange de 5 000 francs\" ?"
                ),
            }

        # ====== 5.b Validate entities (only if intent exists) ======
        is_valid, missing = entity_extractor.validate_entities(intent, entities)

        # ====== 6. Handle missing entities ======
        if not is_valid:
            return {
                "mode": "dev-voice-test",
                "conversation_id": conversation_id,
                "transcription": transcription,
                "detected_language": str(detected_language),
                "stt_confidence": stt_conf,
                "cleaned_text": cleaned,
                "intent": intent,
                "intent_confidence": intent_conf,
                "entities": entities,
                "status": "missing_entities",
                "missing_entities": missing,
                "response": f"Pour continuer, j'ai besoin de: {', '.join(missing)}",
            }

        # ====== 7. Banking orchestrator ======
        result = await banking_orchestrator.process_command(
            intent=intent,
            entities=entities,
            conversation_id=conversation_id,
            user_id=conversation_id,
        )

        # Save conversation to memory
        await memory.add_message(conversation_id, "user", transcription)
        await memory.add_message(conversation_id, "assistant", result["response"])

        # ====== 8. Cleanup temp files ======
        try:
            raw_path.unlink(missing_ok=True)
            preprocessed_path.unlink(missing_ok=True)
        except Exception:
            pass

        # ====== 9. Final JSON ======
        return {
            "mode": "dev-voice-test",
            "conversation_id": conversation_id,
            "transcription": transcription,
            "detected_language": str(detected_language),
            "stt_confidence": stt_conf,
            "cleaned_text": cleaned,
            "intent": intent,
            "intent_confidence": intent_conf,
            "entities": entities,
            "banking_result": result,
            "status": result.get("status", "success"),
        }

    except Exception as e:
        logger.error(f"Dev voice test error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def process_text_with_nlu(conversation_id: str, text: str):
    """
    Process text message with NLU and banking logic
    """
    try:
        text_cleaner = BankingTextCleaner()
        intent_classifier = get_intent_classifier()
        entity_extractor = get_entity_extractor()
        banking_orchestrator = get_banking_orchestrator()
        botpress = get_botpress_client()
        memory = ConversationMemory()

        # 1) Clean text
        cleaned_text = text_cleaner.clean(text)
        logger.info(f"🧹 Cleaned: {cleaned_text}")

        # 2) Intent
        intent, confidence = intent_classifier.classify(cleaned_text)
        logger.info(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")

        if confidence < 0.6:
            await botpress.send_text(
                conversation_id,
                "Désolé, je n'ai pas bien compris votre demande. Pouvez-vous reformuler ?",
            )
            return

        # 3) Entities
        entities = entity_extractor.extract(cleaned_text)
        logger.info(f"📦 Entities: {entities}")

        # 4) Validate entities
        is_valid, missing = entity_extractor.validate_entities(intent, entities)
        if not is_valid:
            missing_str = ", ".join(missing)
            await botpress.send_text(
                conversation_id,
                f"Pour continuer, j'ai besoin de : {missing_str}",
            )
            return

        # 5) Process banking command
        result = await banking_orchestrator.process_command(
            intent=intent,
            entities=entities,
            conversation_id=conversation_id,
            user_id=conversation_id,
        )

        # 6) Memory + reply
        await memory.add_message(conversation_id, "user", text)
        await memory.add_message(conversation_id, "assistant", result["response"])

        await botpress.send_text(conversation_id, result["response"])
        logger.info(f"✅ Banking command processed: {intent}")

    except Exception as e:
        logger.error(f"Error processing text with NLU: {e}", exc_info=True)
        try:
            botpress = get_botpress_client()
            await botpress.send_text(
                conversation_id,
                "Désolé, une erreur s'est produite. Veuillez réessayer.",
            )
        except Exception:
            pass


async def process_audio_with_nlu(conversation_id: str, audio_url: str):
    """
    Process audio message with full NLU pipeline:
    1. Download + preprocess audio
    2. Whisper STT (detects language)
    3. Text cleaning
    4. Intent classification
    5. Entity extraction + validation
    6. Banking orchestration
    7. TTS answer back to the user (voice)
    """

    audio_path: Path | None = None
    preprocessed_path: Path | None = None

    try:
        # Get services
        whisper = get_whisper_service()
        text_cleaner = BankingTextCleaner()
        intent_classifier = get_intent_classifier()
        entity_extractor = get_entity_extractor()
        banking_orchestrator = BankingOrchestrator()
        botpress = get_botpress_client()
        memory = ConversationMemory()
        tts = TTSService()  # or get_tts_service() if you wired it as singleton

        # 1) Download audio
        logger.info("📥 Downloading audio...")
        audio_dir = settings.AUDIO_STORAGE_PATH / "downloads"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_path = audio_dir / f"{uuid.uuid4()}.ogg"
        await botpress.download_audio(audio_url, str(audio_path))

        # 2) Preprocess audio (validation + resample etc.)
        logger.info("🔧 Preprocessing audio...")
        preprocessed_path = await AudioPreprocessor.preprocess(audio_path)

        # Optional: guardrail for duration
        duration = AudioPreprocessor.get_audio_duration(preprocessed_path)
        logger.info(f"⏱️ Audio duration: {duration:.2f}s")

        if duration > MAX_AUDIO_DURATION_SECONDS:
            msg = (
                "Le message vocal est un peu long. "
                "Pouvez-vous reformuler en moins de 30 secondes ?"
            )
            await botpress.send_text(conversation_id, msg)
            return

        # 3) Transcribe with Whisper
        logger.info("🎙️ Transcribing...")
        transcription, detected_language, stt_confidence = await whisper.transcribe(
            preprocessed_path
        )

        logger.info(f"📝 Transcription: {transcription}")
        logger.info(
            f"🌍 Language: {detected_language} (confidence: {stt_confidence:.2%})"
        )

        # Save detected language in memory for future TTS + NLU
        await memory.set_language(conversation_id, detected_language)

        # If transcription is too uncertain, ask to repeat
        if stt_confidence < 0.6 or not transcription.strip():
            await botpress.send_text(
                conversation_id,
                "Je n'ai pas bien entendu votre message, pouvez-vous répéter s'il vous plaît ?",
            )
            return

        # 4) Clean text
        cleaned_text = text_cleaner.clean(transcription)
        logger.info(f"🧹 Cleaned: {cleaned_text}")

        # 5) Classify intent
        intent, intent_confidence =  intent_classifier.classify(cleaned_text)
        logger.info(f"🎯 Intent: {intent} (confidence: {intent_confidence:.2f})")

        if intent_confidence < 0.6:
            await botpress.send_text(
                conversation_id,
                "Désolé, je n'ai pas bien compris votre demande. Pouvez-vous reformuler ?",
            )
            return

        # 6) Extract entities
        entities = entity_extractor.extract(cleaned_text)
        logger.info(f"📦 Entities: {entities}")

        # 7) Validate entities
        is_valid, missing = entity_extractor.validate_entities(intent, entities)

        if not is_valid:
            missing_str = ", ".join(missing)
            await botpress.send_text(
                conversation_id,
                f"Pour continuer, j'ai besoin de : {missing_str}",
            )
            return

        # 8) Process banking command
        result = await banking_orchestrator.process_command(
            intent=intent,
            entities=entities,
            conversation_id=conversation_id,
            user_id=conversation_id,
        )

        response_text = result["response"]

        # 9) Save in conversation memory
        await memory.add_message(conversation_id, "user", transcription)
        await memory.add_message(conversation_id, "assistant", response_text)

        # 10) Generate TTS (voice reply)
        # Map Whisper/CameroonLanguage -> TTS language
        language_for_tts = detected_language
        if language_for_tts not in [
            CameroonLanguage.FRENCH,
            CameroonLanguage.ENGLISH,
        ]:
            # fallback for now
            language_for_tts = CameroonLanguage.FRENCH

        logger.info(f"🔊 Generating TTS in {language_for_tts}...")
        tts_audio_path = await tts.synthesize(
            response_text,
            language=language_for_tts,
        )

        # 11) Send both text + audio to user
        await botpress.send_text(conversation_id, response_text)
        await botpress.send_audio(conversation_id, tts_audio_path)

        logger.info("✅ Audio message processed with NLU + TTS successfully")

    except Exception as e:
        logger.error(f"Error processing audio with NLU: {e}", exc_info=True)
        try:
            botpress = get_botpress_client()
            await botpress.send_text(
                conversation_id,
                "Désolé, je n'ai pas pu traiter votre message vocal.",
            )
        except Exception:
            pass
    finally:
        # Cleanup temp files
        if audio_path and audio_path.exists():
            audio_path.unlink(missing_ok=True)
        if preprocessed_path and preprocessed_path.exists():
            preprocessed_path.unlink(missing_ok=True)
