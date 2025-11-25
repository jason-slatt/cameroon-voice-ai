"""Logging configuration"""

import logging
import sys
from app.config import settings


def setup_logging():
    """Setup logging configuration"""
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)