"""
Centralized logging system.

This module provides a singleton Logger class that handles all logging
for the application with file rotation and optional console output.
"""

from __future__ import annotations

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


class Logger:
    """System log manager using singleton pattern."""

    _instance: Logger | None = None
    _logger: logging.Logger | None = None

    def __new__(cls) -> Logger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._logger is not None:
            return

        self._logger = logging.getLogger("ChurchStreamSync")
        self._logger.setLevel(logging.DEBUG)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Configure log handlers."""
        from src.core.config import get_config

        config = get_config()

        # Clear existing handlers
        if self._logger:
            self._logger.handlers.clear()

        # Standard format
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler (rotating)
        if config.log.enabled and self._logger:
            log_file: Path = config.log_dir / f"church_sync_{datetime.now():%Y%m%d}.log"

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=config.log.max_size_mb * 1024 * 1024,
                backupCount=config.log.backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, config.log.level))
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        # Console handler (optional)
        if config.log.console_output and self._logger:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

    def debug(self, message: str) -> None:
        """Log debug message."""
        if self._logger:
            self._logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        if self._logger:
            self._logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        if self._logger:
            self._logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        if self._logger:
            self._logger.error(message)

    def critical(self, message: str) -> None:
        """Log critical message."""
        if self._logger:
            self._logger.critical(message)

    def exception(self, message: str) -> None:
        """Log exception with traceback."""
        if self._logger:
            self._logger.exception(message)


# Global instance
_logger_instance: Logger | None = None


def get_logger() -> Logger:
    """Return the global logger instance."""
    global _logger_instance  # noqa: PLW0603
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance


# Convenience functions
def debug(message: str) -> None:
    """Log debug message."""
    get_logger().debug(message)


def info(message: str) -> None:
    """Log info message."""
    get_logger().info(message)


def warning(message: str) -> None:
    """Log warning message."""
    get_logger().warning(message)


def error(message: str) -> None:
    """Log error message."""
    get_logger().error(message)


def critical(message: str) -> None:
    """Log critical message."""
    get_logger().critical(message)


def exception(message: str) -> None:
    """Log exception with traceback."""
    get_logger().exception(message)
