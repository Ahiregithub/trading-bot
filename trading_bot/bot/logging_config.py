"""
Logging configuration for the trading bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure root logger with rotating file handler and console handler.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured root logger instance.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter

    # Avoid duplicate handlers on re-import
    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- Rotating file handler (DEBUG+) ---
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # --- Console handler (INFO+ by default) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger."""
    return logging.getLogger(name)
