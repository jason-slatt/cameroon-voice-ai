"""Application settings and configuration"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Info
    APP_NAME: str = "BAFOKA Voice Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_TO_FILE: bool = True
    LOG_TO_CONSOLE: bool = True
    LOG_DIR: str = "logs"
    
    # Company Info
    COMPANY_NAME: str = "BAFOKA"
    CURRENCY: str = "XAF"
    CURRENCY_SYMBOL: str = "FCFA"
    
    # Transaction Limits (in XAF)
    WITHDRAWAL_MIN: float = 500.0
    WITHDRAWAL_MAX: float = 500000.0
    WITHDRAWAL_DAILY_LIMIT: float = 1000000.0
    TOPUP_MIN: float = 500.0
    TOPUP_MAX: float = 2000000.0
    
    # Backend API
    BACKEND_BASE_URL: str = "https://sandbox.bafoka.network"
    BACKEND_API_KEY: Optional[str] = None
    BACKEND_TIMEOUT: int = 30
    
    # LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3"
    MAX_RESPONSE_WORDS: int = 50
    
    # Speech-to-Text
    WHISPER_MODEL: str = "base.en"
    STT_ENABLED: bool = True
    
    # Text-to-Speech
    TTS_ENABLED: bool = True
    TTS_EXAGGERATION: float = 0.5
    TTS_CFG_WEIGHT: float = 0.5
    TTS_VOICE_PATH: Optional[str] = None
    
    # Audio Storage
    AUDIO_STORAGE_PATH: str = "audio_files"
    AUDIO_BASE_URL: str = "http://localhost:8000/audio"
    AUDIO_FORMAT: str = "wav"
    AUDIO_CLEANUP_HOURS: int = 24
    
    # Storage
    REDIS_URL: Optional[str] = None
    CONVERSATION_TTL: int = 3600
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()