"""Structured logging configuration for Mitchell using loguru."""

import sys
from pathlib import Path
from loguru import logger
from mitchell.core.config import settings


def setup_logging(log_file: bool = True) -> None:
    """Configure loguru logging based on application settings."""
    logger.remove()

    # Console sink
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # Optional file sink in data directory
    if log_file:
        log_dir = Path(settings.data_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / "mitchell.log"
        logger.add(
            str(file_path),
            level=settings.log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        )


# Initialize logging upon import
setup_logging(log_file=False)

__all__ = ["logger", "setup_logging"]
