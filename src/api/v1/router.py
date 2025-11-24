# src/api/v1/router.py
"""
Main API router
"""
from fastapi import APIRouter

from src.api.v1.endpoints import webhook

api_router = APIRouter()

api_router.include_router(
    webhook.router,
    prefix="/webhook",
    tags=["Webhook"]
)