"""Middleware that binds request context and logs every update."""

from __future__ import annotations

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from collections.abc import Awaitable, Callable
from typing import Any

from bot.utils.logging import get_logger

_log = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Attach a per-update context (user id, update type) to all log lines."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Bind contextvars, log the incoming update, then delegate."""
        tg_user = data.get("event_from_user")
        structlog.contextvars.clear_contextvars()
        if tg_user is not None:
            structlog.contextvars.bind_contextvars(user_id=tg_user.id)

        if isinstance(event, Message) and event.text:
            _log.info("message", text=event.text[:128])
        elif isinstance(event, CallbackQuery):
            _log.info("callback", data=event.data)

        try:
            return await handler(event, data)
        except Exception as exc:  # noqa: BLE001 - log & re-raise for visibility
            _log.error("handler_error", error=str(exc), exc_info=True)
            raise
