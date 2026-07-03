"""Middleware that injects a fresh async DB session into every handler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import get_session


class DatabaseMiddleware(BaseMiddleware):
    """Provide a transactional ``session`` to handlers via ``data``.

    The session is committed automatically when the handler returns and rolled
    back if it raises, keeping every update atomic.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Open a session, expose it to the handler, and clean it up."""
        async with get_session() as session:
            data["session"] = session
            return await handler(event, data)
