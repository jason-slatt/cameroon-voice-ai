"""
Custom exceptions for clear error handling
"""
from typing import Any


class BaseAppException(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AudioProcessingError(BaseAppException):
    """Raised when audio processing fails"""
    pass


class TranscriptionError(BaseAppException):
    """Raised when transcription fails"""
    pass


class LanguageDetectionError(BaseAppException):
    """Raised when language detection fails"""
    pass


class LLMInferenceError(BaseAppException):
    """Raised when LLM inference fails"""
    pass


class TTSGenerationError(BaseAppException):
    """Raised when TTS generation fails"""
    pass


class WhatsAppError(BaseAppException):
    """Raised when WhatsApp integration fails"""
    pass


class ValidationError(BaseAppException):
    """Raised when input validation fails"""
    pass


class ResourceNotFoundError(BaseAppException):
    """Raised when requested resource doesn't exist"""
    pass


class RateLimitExceededError(BaseAppException):
    """Raised when rate limit is exceeded"""
    pass