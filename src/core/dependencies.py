# src/core/dependencies.py
"""
Global dependencies for the entire application
"""
from __future__ import annotations

from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from src.core.config import settings
from src.core.logging import logger

from src.services.whisper.service import WhisperService
from src.services.tts.service import TTSService
from src.services.botpress.client import BotpressClient
from src.services.nlu.intent_classifier import ZeroShotIntentClassifier
from src.services.nlu.entity_extractor import BankingEntityExtractor


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

_redis_pool: Optional[redis.Redis] = None


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


async def close_redis() -> None:
    """Close Redis on shutdown"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


# ==================== SERVICES (AI / BOT / BANKING) ====================

_whisper: Optional[WhisperService] = None
_tts: Optional[TTSService] = None
_botpress: Optional[BotpressClient] = None
_intent_classifier: Optional[ZeroShotIntentClassifier] = None
_entity_extractor: Optional[BankingEntityExtractor] = None
_banking_orchestrator: "BankingOrchestrator | None" = None  # lazy import type


def get_whisper_service() -> WhisperService:
    """Get Whisper service"""
    if _whisper is None:
        raise RuntimeError("Whisper service not initialized")
    return _whisper


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


def get_intent_classifier() -> ZeroShotIntentClassifier:
    """Get intent classifier instance"""
    if _intent_classifier is None:
        raise RuntimeError("Intent classifier not initialized")
    return _intent_classifier


def get_entity_extractor() -> BankingEntityExtractor:
    """Get entity extractor instance"""
    if _entity_extractor is None:
        raise RuntimeError("Entity extractor not initialized")
    return _entity_extractor


def get_banking_orchestrator() -> "BankingOrchestrator":
    """
    Get BankingOrchestrator instance (singleton).

    Lazy import to avoid circular dependency:
    - dependencies.py -> orchestrator.py -> security.py -> dependencies.py
    """
    global _banking_orchestrator

    if _banking_orchestrator is None:
        # ⬇️ Import ici et PAS en haut du fichier
        from src.services.banking.orchestrator import BankingOrchestrator

        _banking_orchestrator = BankingOrchestrator()

    return _banking_orchestrator


async def initialize_services() -> None:
    """
    Load all services on startup.

    Called once from FastAPI lifespan in `main.py`.
    """
    global _whisper, _tts, _botpress, _intent_classifier, _entity_extractor

    logger.info("🚀 Initializing services...")

    # Whisper
    _whisper = WhisperService()
    await _whisper.initialize()

     # try:
    #     _tts = TTSService()
    #     await _tts.initialize()
    # except Exception as e:
    #     logger.error(f"❌ Failed to initialize TTS: {e}")
    #     _tts = None
    # NLU: Intent classifier
    _intent_classifier = ZeroShotIntentClassifier()
    await _intent_classifier.initialize()

    # NLU: rule-based entity extractor
    _entity_extractor = BankingEntityExtractor()

    # Botpress HTTP client
    _botpress = BotpressClient()

    logger.info("✅ All services ready")


async def cleanup_services() -> None:
    """Cleanup on shutdown"""
    global _whisper, _tts, _botpress

    logger.info("🛑 Shutting down services...")

    if _whisper:
        await _whisper.cleanup()
        _whisper = None

    if _tts:
        await _tts.cleanup()
        _tts = None

    # Botpress: rien de spécial pour l’instant

    await close_redis()
    logger.info("✅ Cleanup complete")
