"""Structured logging based on :mod:`structlog`.

Provides five logical channels through a single logger:
``info``, ``warning``, ``error``, ``security`` and ``audit`` — differentiated
by the ``channel`` bound field so they can be filtered downstream.

Logs are emitted as JSON (via ``orjson``) to stdout and, optionally, appended
to ``logs/app.jsonl``. JSON keeps the footprint tiny and machine-parseable,
which is ideal for a 1 GB RAM VPS.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import orjson
import structlog

_LOG_DIR = Path("logs")


def _orjson_dumps(obj: Any, *, default: Any) -> str:
    """Serialize a log event to a JSON string using orjson (fast, low-mem)."""
    return orjson.dumps(obj, default=default).decode("utf-8")


def configure_logging(level: str = "INFO", log_to_file: bool = True) -> None:
    """Configure structlog + stdlib logging.

    Args:
        level: Logging threshold (``DEBUG``/``INFO``/``WARNING``/``ERROR``).
        log_to_file: When ``True`` a JSON-lines file is written to ``logs/``.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_to_file:
        _LOG_DIR.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(_LOG_DIR / "app.jsonl", encoding="utf-8"))

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level, logging.INFO),
        handlers=handlers,
    )

    # Silence noisy third-party loggers to conserve resources.
    for noisy in ("aiogram.event", "aiosqlite", "httpx", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(serializer=_orjson_dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, channel: str = "info") -> structlog.stdlib.BoundLogger:
    """Return a bound logger pre-tagged with a module name and channel.

    Args:
        name: Logical logger name (usually ``__name__``).
        channel: One of ``info``, ``warning``, ``error``, ``security``,
            ``audit`` — used for downstream filtering.
    """
    return structlog.get_logger(name).bind(channel=channel)
