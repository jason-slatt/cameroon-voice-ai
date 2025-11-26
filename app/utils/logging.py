"""Logging configuration"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime

from app.config import settings


def setup_logging(
    log_dir: str = "logs",
    log_to_file: bool = True,
    log_to_console: bool = True,
):
    """
    Setup logging configuration with file and console handlers.
    
    Args:
        log_dir: Directory to store log files
        log_to_file: Whether to log to files
        log_to_console: Whether to log to console
    """
    # Create logs directory
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
    
    # Determine log level
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if log_to_file:
        # Main application log (rotating by size)
        app_log_file = log_path / "app.log"
        file_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Error log (only errors and critical)
        error_log_file = log_path / "error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Daily log (rotating daily)
        daily_log_file = log_path / f"daily_{datetime.now().strftime('%Y%m%d')}.log"
        daily_handler = TimedRotatingFileHandler(
            daily_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(daily_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(f"Logging initialized - Level: {logging.getLevelName(level)}")
    if log_to_file:
        root_logger.info(f"Logs directory: {log_path.absolute()}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_request(
    logger: logging.Logger,
    user_id: str,
    conversation_id: str,
    message: str,
    intent: str = None,
):
    """
    Log a user request in a structured format.
    
    Args:
        logger: Logger instance
        user_id: User identifier
        conversation_id: Conversation identifier
        message: User message
        intent: Detected intent (optional)
    """
    log_data = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "message": message[:100],  # Truncate long messages
        "intent": intent,
    }
    logger.info(f"REQUEST: {log_data}")


def log_response(
    logger: logging.Logger,
    user_id: str,
    conversation_id: str,
    response: str,
    processing_time_ms: int = None,
):
    """
    Log an assistant response in a structured format.
    
    Args:
        logger: Logger instance
        user_id: User identifier
        conversation_id: Conversation identifier
        response: Assistant response
        processing_time_ms: Processing time in milliseconds
    """
    log_data = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "response": response[:100],  # Truncate long responses
        "processing_time_ms": processing_time_ms,
    }
    logger.info(f"RESPONSE: {log_data}")