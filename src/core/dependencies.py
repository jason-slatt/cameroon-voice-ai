# src/core/dependencies.py
"""
Global dependencies for the entire application
"""
from functools import lru_cache
from typing import AsyncGenerator

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.core.config import settings
from src.core.logging import logger


# ==================== DATABASE ====================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== REDIS ====================

_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Redis client (singleton)"""
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        logger.info("✅ Redis connected")
    
    return _redis_pool


async def close_redis():
    """Close Redis on shutdown"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


# ==================== AI SERVICES ====================

from src.services.whisper.service import WhisperService
from src.services.llama.service import LlamaService
from src.services.tts.service import TTSService
from src.services.botpress.client import BotpressClient

# Global instances (loaded once on startup)
_whisper: WhisperService | None = None
_llama: LlamaService | None = None
_tts: TTSService | None = None
_botpress: BotpressClient | None = None


def get_whisper_service() -> WhisperService:
    """Get Whisper service"""
    if _whisper is None:
        raise RuntimeError("Whisper service not initialized")
    return _whisper


def get_llama_service() -> LlamaService:
    """Get LLaMA service"""
    if _llama is None:
        raise RuntimeError("LLaMA service not initialized")
    return _llama


def get_tts_service() -> TTSService:
    """Get TTS service"""
    if _tts is None:
        raise RuntimeError("TTS service not initialized")
    return _tts


def get_botpress_client() -> BotpressClient:
    """Get Botpress client"""
    if _botpress is None:
        raise RuntimeError("Botpress client not initialized")
    return _botpress


async def initialize_services():
    """Load all AI models on startup"""
    global _whisper, _llama, _tts, _botpress
    
    logger.info("🚀 Initializing services...")
    
    # Initialize services
    _whisper = WhisperService()
    await _whisper.initialize()
    
    _llama = LlamaService()
    await _llama.initialize()
    
   # _tts = TTSService()
    #await _tts.initialize()
    
    _botpress = BotpressClient()
    
    logger.info("✅ All services ready")


async def cleanup_services():
    """Cleanup on shutdown"""
    global _whisper, _llama, _tts, _botpress
    
    logger.info("🛑 Shutting down services...")
    
    if _whisper:
        await _whisper.cleanup()
    if _llama:
        await _llama.cleanup()
    if _tts:
        await _tts.cleanup()
    
    await close_redis()
    
    logger.info("✅ Cleanup complete")