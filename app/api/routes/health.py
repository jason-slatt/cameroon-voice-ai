"""Health check endpoints"""

from fastapi import APIRouter
from app.api.schemas import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = {
        "api": "healthy",
        "backend": "unknown",  # TODO: Add backend health check
    }
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        services=services,
    )