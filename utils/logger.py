"""
AetherWatch — Centralised Logging
Uses loguru for structured, colourful console + file logging.
"""

import sys
from loguru import logger
from config.settings import LOG_LEVEL

# Remove the default handler
logger.remove()

# Console handler — coloured, human-readable
logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# File handler — full detail, rotating
logger.add(
    "aetherwatch.log",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
)

__all__ = ["logger"]
def get_logger(name=None):
    return logger