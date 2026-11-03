"""Structured logging system for JARVIS.

Provides thread-safe, colored console logging via Rich and rotating file logs.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from rich.logging import RichHandler


_is_initialized = False


def setup_logging(
    log_dir: Path | None = None,
    log_level: str = "INFO",
    app_name: str = "JARVIS",
) -> None:
    """Initialize root and JARVIS loggers with console and file handlers."""
    global _is_initialized
    if _is_initialized:
        return

    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. Console Handler using Rich
    rich_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=False,
    )
    rich_handler.setLevel(level)
    root_logger.addHandler(rich_handler)

    # 2. Rotating File Handler
    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "jarvis.log"
            file_handler = RotatingFileHandler(
                filename=str(log_file),
                maxBytes=10 * 1024 * 1024,  # 10 MB per file
                backupCount=5,
                encoding="utf-8",
            )
            file_formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
        except OSError:
            pass

    _is_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with the given name."""
    if not _is_initialized:
        # Fallback basic initialization if called before explicit setup
        logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)
