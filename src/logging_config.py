"""
Structured logging for the Multi-Agent RAG System.

Emits JSON lines to both stdout and a log file, so query lifecycle events
(incoming query, agent selected, sources retrieved, generated SQL, timing,
errors) can be grepped or shipped to a log aggregator.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from src.config import settings

_LOGGER_NAME = "multiagent_rag"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(settings.log_level)
    formatter = JsonFormatter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    try:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Fall back to stdout-only logging if the filesystem isn't writable
        # (e.g. some restricted CI environments).
        pass

    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: str, message: str, **fields: Any) -> None:
    """Emit a structured log line with arbitrary key/value fields attached."""
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(message, extra={"extra_fields": fields})


class Timer:
    """Small context manager for timing a block and logging its duration_ms."""

    def __init__(self, logger: logging.Logger, event: str, **fields: Any) -> None:
        self.logger = logger
        self.event = event
        self.fields = fields
        self._start = 0.0
        self.duration_ms = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.duration_ms = round((time.perf_counter() - self._start) * 1000, 2)
        status = "error" if exc_type else "ok"
        log_event(
            self.logger,
            "error" if exc_type else "info",
            self.event,
            status=status,
            duration_ms=self.duration_ms,
            **self.fields,
        )
        