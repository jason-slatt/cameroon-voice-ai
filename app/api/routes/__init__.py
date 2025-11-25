from fastapi import APIRouter
from .chat import router as chat_router
from .voice import router as voice_router
from .health import router as health_router
from .audio import router as audio_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(voice_router, prefix="/voice", tags=["Voice"])

# Audio serving at root level
audio_api_router = audio_router