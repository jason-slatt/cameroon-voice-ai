# src/core/logging.py
"""
Structured logging configuration with context
"""
import logging
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.core.config import settings


class InterceptHandler(logging.Handler):
    """Intercept standard logging and route to loguru"""
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure application logging"""
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    
    # File handler (JSON for production)
    log_path = Path("./logs")
    log_path.mkdir(exist_ok=True)
    
    if settings.ENVIRONMENT == "production":
        logger.add(
            log_path / "app.log",
            rotation="500 MB",
            retention="10 days",
            compression="zip",
            level="INFO",
            serialize=True,  # JSON format
        )
    else:
        logger.add(
            log_path / "app.log",
            rotation="100 MB",
            retention="7 days",
            level="DEBUG",
        )
    
    # Error file
    logger.add(
        log_path / "error.log",
        rotation="100 MB",
        retention="30 days",
        level="ERROR",
        backtrace=True,
        diagnose=True,
    )
    
    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Suppress noisy libraries
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)


def log_model_info(model_name: str, params: dict[str, Any]) -> None:
    """Log model loading information"""
    logger.info(
        f"Loading {model_name}",
        extra={
            "model": model_name,
            "parameters": params,
        }
    )


def log_request(
    endpoint: str,
    method: str,
    user_id: str | None,
    duration_ms: float,
) -> None:
    """Log API request"""
    logger.info(
        f"{method} {endpoint}",
        extra={
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "duration_ms": duration_ms,
        }
    )


def log_error(
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """Log error with context"""
    logger.error(
        f"Error: {str(error)}",
        extra={"error_type": type(error).__name__, "context": context or {}},
    )