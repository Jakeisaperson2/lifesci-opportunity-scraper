import os
import sys
from loguru import logger


def setup_logging():
    """Configure loguru for console + rotating file output."""
    logger.remove()  # Remove default handler

    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "logs/app.log")

    # Console: human-readable, colored
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # File: structured, rotating at 10 MB, keep 7 days
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )
