# src/core/config.py
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # ==================== APPLICATION ====================
    APP_NAME: str = "Cameroon Voice AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = Field(default=False)
    
    # ==================== API ====================
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: list[str] = Field(default=["*"])
    CORS_ORIGINS: list[str] = Field(default=["*"])
    
    # ==================== DATABASE ====================
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    
    # ==================== REDIS ====================
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CACHE_TTL_SECONDS: int = Field(default=3600)
    SESSION_TTL_SECONDS: int = Field(default=86400)  # 24 hours
    
    # ==================== GPU & COMPUTE ====================
    DEVICE: Literal["cuda", "cpu", "mps"] = Field(default="cuda")
    MIXED_PRECISION: bool = Field(default=True)
    MAX_BATCH_SIZE: int = Field(default=8)
    USE_QUANTIZATION: bool = Field(default=True)
    
    # ==================== WHISPER (STT) ====================
    WHISPER_MODEL_PATH: str = Field(..., env="WHISPER_MODEL_PATH")
    WHISPER_DEVICE: str = Field(default="cuda", env="WHISPER_DEVICE")  # ADD THIS LINE
    WHISPER_COMPUTE_TYPE: Literal["float16", "float32", "int8"] = "float16"
    
    # ==================== LLAMA (LLM) ====================
    LLAMA_MODEL_PATH: str = Field(..., env="LLAMA_MODEL_PATH")
    LLAMA_MODEL_NAME: str = Field(default="meta-llama/Llama-2-7b-chat-hf")
    LLAMA_USE_QLORA: bool = Field(default=True)
    LLAMA_MAX_NEW_TOKENS: int = Field(default=512)
    LLAMA_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    LLAMA_TOP_P: float = Field(default=0.9, ge=0.0, le=1.0)
    LLAMA_REPETITION_PENALTY: float = Field(default=1.1, ge=1.0, le=2.0)
    
    # ==================== COQUI TTS ====================
    TTS_MODEL_PATH: str = Field(..., env="TTS_MODEL_PATH")
    TTS_VOCODER_PATH: str = Field(..., env="TTS_VOCODER_PATH")
    TTS_CONFIG_PATH: str = Field(..., env="TTS_CONFIG_PATH")
    TTS_SPEAKERS_PATH: str = Field(..., env="TTS_SPEAKERS_PATH")
    TTS_SAMPLE_RATE: int = Field(default=22050)
    
    # ==================== AUDIO PROCESSING ====================
    AUDIO_SAMPLE_RATE: int = Field(default=16000)
    AUDIO_MAX_DURATION_SECONDS: int = Field(default=300)
    AUDIO_MAX_SIZE_MB: int = Field(default=25)
    AUDIO_STORAGE_PATH: Path = Field(default=Path("./storage/audio"))
    AUDIO_CLEANUP_HOURS: int = Field(default=24)
    
    # ==================== BOTPRESS ====================
    BOTPRESS_URL: str = Field(..., env="BOTPRESS_URL")
    BOTPRESS_BOT_ID: str = Field(..., env="BOTPRESS_BOT_ID")
    BOTPRESS_API_TOKEN: str = Field(..., env="BOTPRESS_API_TOKEN")
    
    # ==================== MONITORING ====================
    SENTRY_DSN: str | None = Field(default=None, env="SENTRY_DSN")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    ENABLE_METRICS: bool = Field(default=True)
    METRICS_PORT: int = Field(default=9090)
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_PER_MINUTE: int = Field(default=30)
    RATE_LIMIT_BURST: int = Field(default=10)
    
    # ==================== TIMEOUTS ====================
    TRANSCRIPTION_TIMEOUT: int = Field(default=60)
    LLM_TIMEOUT: int = Field(default=30)
    TTS_TIMEOUT: int = Field(default=45)
    WHATSAPP_TIMEOUT: int = Field(default=10)
    
    @field_validator("DEVICE")
    def validate_device(cls, value: str) -> str:
        """Ensure device is valid"""
        import torch
        
        if value == "cuda" and not torch.cuda.is_available():
            return "cpu"
        if value == "mps" and not torch.backends.mps.is_available():
            return "cpu"
        return value
    
    @field_validator("AUDIO_STORAGE_PATH")
    def create_storage_path(cls, value: Path) -> Path:
        """Create storage directory if not exists"""
        value.mkdir(parents=True, exist_ok=True)
        return value
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


settings = get_settings()