from fastapi import APIRouter

from app.api.v1.endpoints import health, voice_turn, audio

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(voice_turn.router)
api_router.include_router(audio.router)