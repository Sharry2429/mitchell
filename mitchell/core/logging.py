"""Structured logging configuration for Mitchell with Loguru and standard logging fallback."""

import logging
import sys
from pathlib import Path
from mitchell.core.config import settings

try:
    from loguru import logger as _loguru_logger

    def setup_logging(log_file: bool = True) -> None:
        """Configure loguru logging based on application settings."""
        _loguru_logger.remove()

        # Console sink
        _loguru_logger.add(
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
            _loguru_logger.add(
                str(file_path),
                level=settings.log_level,
                rotation="10 MB",
                retention="7 days",
                compression="zip",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            )

    logger = _loguru_logger
    setup_logging(log_file=False)

except ImportError:
    # Standard library logging wrapper matching Loguru string formatting
    class FallbackLogger:
        def __init__(self) -> None:
            self._logger = logging.getLogger("mitchell")
            logging.basicConfig(
                level=getattr(logging, settings.log_level, logging.INFO),
                format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
            )

        def _format(self, msg: str, *args, **kwargs) -> str:
            if args or kwargs:
                try:
                    return msg.format(*args, **kwargs)
                except Exception:
                    return msg
            return msg

        def debug(self, msg: str, *args, **kwargs) -> None:
            self._logger.debug(self._format(msg, *args, **kwargs))

        def info(self, msg: str, *args, **kwargs) -> None:
            self._logger.info(self._format(msg, *args, **kwargs))

        def warning(self, msg: str, *args, **kwargs) -> None:
            self._logger.warning(self._format(msg, *args, **kwargs))

        def error(self, msg: str, *args, **kwargs) -> None:
            self._logger.error(self._format(msg, *args, **kwargs))

        def exception(self, msg: str, *args, **kwargs) -> None:
            self._logger.exception(self._format(msg, *args, **kwargs))

    logger = FallbackLogger()

    def setup_logging(log_file: bool = True) -> None:
        pass


__all__ = ["logger", "setup_logging"]
