import json
import logging
import os
import sys
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pid": os.getpid(),  # Include process ID for multi-worker debugging
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        return json.dumps(log_data)


# Track which loggers have been configured per process to avoid duplicates
_configured_loggers: dict[tuple[str, int], bool] = {}


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance with JSON formatting

    Notes:
        - Uses process-specific tracking to prevent duplicate handlers in Uvicorn multi-worker mode
        - Sets propagate=False to prevent duplicate logs from parent loggers
    """
    logger = logging.getLogger(name)
    pid = os.getpid()
    logger_key = (name, pid)

    # Check if this logger has already been configured for this process
    if logger_key in _configured_loggers:
        return logger

    # Configure logger
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Prevent duplicate logs in Uvicorn

    # Only add handler if none exist for this logger
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    # Mark as configured for this process
    _configured_loggers[logger_key] = True

    return logger
