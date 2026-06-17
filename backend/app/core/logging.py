"""Structured JSON logging with request tracing and correlation IDs"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings

# Context variable for correlation/request ID propagation
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(cid)


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return request_id_var.get()


def set_request_id(rid: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(rid)


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter that emits one JSON object per line.
    Includes correlation IDs, request IDs, and optional extra fields.
    """

    RESERVED_ATTRS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        log_object: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": settings.ENVIRONMENT,
        }

        # Attach tracing identifiers when available
        cid = correlation_id_var.get()
        rid = request_id_var.get()
        if cid:
            log_object["correlation_id"] = cid
        if rid:
            log_object["request_id"] = rid

        # Serialize exception info
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_object["stack_info"] = self.formatStack(record.stack_info)

        # Merge any extra fields attached to the record
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_"):
                try:
                    json.dumps(value)  # verify it is JSON-serialisable
                    log_object[key] = value
                except (TypeError, ValueError):
                    log_object[key] = str(value)

        return json.dumps(log_object, default=str)


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure structured JSON logging for the entire application.

    Args:
        level: Log level string (DEBUG/INFO/WARNING/ERROR/CRITICAL).
               Falls back to settings.LOG_LEVEL when not supplied.
    """
    effective_level = (level or settings.LOG_LEVEL).upper()

    root_logger = logging.getLogger()
    root_logger.setLevel(effective_level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(effective_level)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-level logger.  Call this instead of logging.getLogger so
    that callers automatically inherit the structured formatter.
    """
    return logging.getLogger(name)
