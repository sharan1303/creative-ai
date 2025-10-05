"""Structured logging configuration

Provides consistent logging across all modules with configurable levels.
"""

import logging
import sys

from src.utils.config import settings


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger with appropriate formatting and level
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))

        # Console handler with UTF-8 encoding support
        import io

        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        handler = logging.StreamHandler(utf8_stdout)
        handler.setLevel(getattr(logging, settings.LOG_LEVEL))

        # Format: timestamp - level - module - message
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False

    return logger
