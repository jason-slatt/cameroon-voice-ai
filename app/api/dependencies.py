"""FastAPI dependencies"""

from app.core.conversation.manager import ConversationManager
from app.storage import (
    get_conversation_store, 
    get_audio_storage as get_audio_storage_service
)
from app.services.speech import (
    get_stt_service as get_stt_service_singleton,
    get_tts_service as get_tts_service_singleton
)


def get_conversation_manager():
    """Get conversation manager"""
    store = get_conversation_store()
    return ConversationManager(store)


def get_stt_service():
    """Dependency for STT service"""
    return get_stt_service_singleton()


def get_tts_service():
    """Dependency for TTS service"""
    return get_tts_service_singleton()


def get_audio_storage():
    """Dependency for audio storage"""
    return get_audio_storage_service()