"""Logging configuration for the AI agent toolbox."""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent.log"

_CONFIGURED = False


def setup_logging(
    level: int = logging.INFO,
    console_level: int = logging.WARNING,
) -> logging.Logger:
    """Configure logging: INFO+ to file, WARNING+ to console (idempotent)."""
    global _CONFIGURED

    logger = logging.getLogger("agent")
    logger.setLevel(level)
    logger.propagate = False

    if _CONFIGURED:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _CONFIGURED = True
    logger.info("Logging initialized")
    return logger
