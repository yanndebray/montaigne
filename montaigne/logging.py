"""Logging configuration for Montaigne."""

import logging
import sys
from typing import Optional

# Package logger
logger = logging.getLogger("montaigne")

# Custom formatter with colors for terminal
class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log levels for terminal output."""

    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors and sys.stderr.isatty():
            color = self.COLORS.get(record.levelno, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    verbose: bool = False,
    quiet: bool = False,
    log_file: Optional[str] = None,
    use_colors: bool = True,
) -> None:
    """Configure logging for the application.

    Args:
        verbose: If True, set level to DEBUG
        quiet: If True, set level to ERROR only
        log_file: Optional path to write logs to file
        use_colors: If True, use colored output in terminal
    """
    # Determine log level
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR
    else:
        level = logging.INFO

    # Configure root montaigne logger
    logger = logging.getLogger("montaigne")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)

    # Use colored formatter for console
    console_fmt = "%(levelname)s: %(message)s"
    if verbose:
        console_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    console_formatter = ColoredFormatter(console_fmt, datefmt="%H:%M:%S", use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        file_formatter = logging.Formatter(file_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"montaigne.{name.split('.')[-1]}")
