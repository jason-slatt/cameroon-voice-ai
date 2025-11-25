"""FastAPI dependencies"""

from functools import lru_cache
from app.core.conversation.manager import ConversationManager
from app.storage import get_conversation_store, get_audio_storage
from app.services.speech import get_stt_service, get_tts_service


@lru_cache()
def get_conversation_store_instance():
    """Get cached conversation store"""
    return get_conversation_store()


def get_conversation_manager():
    """Get conversation manager (create new instance per request)"""
    store = get_conversation_store()
    return ConversationManager(store)


def get_stt_service():
    """Dependency for STT service"""
    return get_stt_service()


def get_tts_service():
    """Dependency for TTS service"""
    return get_tts_service()


def get_audio_storage():
    """Dependency for audio storage"""
    return get_audio_storage()