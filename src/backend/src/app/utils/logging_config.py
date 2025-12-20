"""
Centralized logging configuration for ViolaDocs backend
"""
import logging
import sys
from typing import Optional


def setup_logging(log_level: Optional[str] = None):
    """
    Setup centralized logging configuration
    
    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  If None, will use settings.log_level
    """
    # Import here to avoid circular imports
    from ..config import settings
    
    # Use provided log_level or fallback to settings
    level_str = log_level or settings.log_level
    log_level_value = getattr(logging, level_str.upper(), logging.INFO)
    
    # Format: timestamp - module - level - message
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level_value,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing configuration
    )
    
    # Configure uvicorn logging
    logging.getLogger("uvicorn").setLevel(log_level_value)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce access log noise
    
    # Configure third-party loggers to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

