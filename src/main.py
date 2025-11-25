# src/main.py
"""
FastAPI app entrypoint
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import setup_logging, logger
from src.core.dependencies import (
    initialize_services,
    cleanup_services,
    get_whisper_service,
    get_intent_classifier,
)
from src.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""

    setup_logging()
    logger.info(f"🚀 Starting {settings.APP_NAME}")

    # Load models and services (Whisper, TTS, NLU, Botpress, Redis)
    await initialize_services()

    logger.info("✅ Ready!")

    yield

    await cleanup_services()
    logger.info("👋 Stopped")


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "running", "app": settings.APP_NAME}


@app.get("/health")
async def health():
    whisper = get_whisper_service()
    intent_classifier = get_intent_classifier()

    return {
        "status": "healthy",
        "whisper_ready": whisper.is_ready(),
        "nlu_ready": intent_classifier.is_ready(),
    }
