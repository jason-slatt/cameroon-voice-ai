"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.api.v1.router import api_router
from app.clients import get_bafoka_client
from app.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging(
        log_dir=settings.LOG_DIR,
        log_to_file=settings.LOG_TO_FILE,
        log_to_console=settings.LOG_TO_CONSOLE,
    )
    
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    logger.info(f"Backend: {settings.BACKEND_BASE_URL}")
    
    # Create audio storage directory
    audio_path = Path(settings.AUDIO_STORAGE_PATH)
    audio_path.mkdir(parents=True, exist_ok=True)
    (audio_path / "responses").mkdir(exist_ok=True)
    (audio_path / "uploads").mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    backend_client = get_bafoka_client()
    await backend_client.close()
    logger.info("Application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Voice assistant API for BAFOKA financial services",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }