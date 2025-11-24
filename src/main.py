# src/main.py
"""
FastAPI app
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import setup_logging, logger
from src.core.dependencies import initialize_services, cleanup_services
from src.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    
    setup_logging()
    logger.info(f"🚀 Starting {settings.APP_NAME}")
    
    # Load AI models
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
    from src.core.dependencies import get_llama_service
    
    llama = get_llama_service()
    
    return {
        "status": "healthy",
        "llama_ready": llama.is_ready(),
    }
