"""Structured logging for SNP Tool.

Provides both human-readable console output and JSON format for machine parsing.
Per Constitution V: Observability & Debuggability.
"""

import logging
import json
import sys
from typing import Any, Optional
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        # Format: [LEVEL] message (extra data if present)
        message = f"{color}[{record.levelname}]{reset} {record.getMessage()}"

        if hasattr(record, "extra_data") and record.extra_data:
            # Format extra data as key=value pairs
            extra_str = " ".join(f"{k}={v}" for k, v in record.extra_data.items())
            message += f" ({extra_str})"

        return message


class SNPToolLogger:
    """Logger wrapper with structured logging support."""

    def __init__(self, name: str, level: int = logging.INFO, json_output: bool = False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []  # Clear existing handlers

        handler = logging.StreamHandler(sys.stderr)
        if json_output:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(ConsoleFormatter())

        self.logger.addHandler(handler)

    def _log(self, level: int, message: str, extra_data: Optional[dict] = None):
        """Log with optional extra data."""
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "",
            0,
            message,
            (),
            None,
        )
        if extra_data:
            record.extra_data = extra_data
        self.logger.handle(record)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, kwargs if kwargs else None)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, kwargs if kwargs else None)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, kwargs if kwargs else None)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, kwargs if kwargs else None)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, kwargs if kwargs else None)


# Global logger instance
_logger: Optional[SNPToolLogger] = None


def get_logger(json_output: bool = False, level: int = logging.INFO) -> SNPToolLogger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = SNPToolLogger("snp_tool", level=level, json_output=json_output)
    return _logger


def configure_logging(verbose: bool = False, json_output: bool = False) -> SNPToolLogger:
    """Configure and return the logger with specified settings."""
    global _logger
    level = logging.DEBUG if verbose else logging.INFO
    _logger = SNPToolLogger("snp_tool", level=level, json_output=json_output)
    return _logger
