"""Anti-flood throttling middleware.

Implements a simple per-user cooldown using a tiny in-memory timestamp map.
No Redis needed — the map is periodically pruned to keep memory bounded.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser

from bot.config import get_settings
from bot.utils.logging import get_logger

_log = get_logger(__name__, channel="security")

# Prune the timestamp map once it grows beyond this many users.
_PRUNE_THRESHOLD = 10_000


class ThrottlingMiddleware(BaseMiddleware):
    """Reject messages sent faster than ``throttle_rate`` seconds apart."""

    def __init__(self) -> None:
        """Initialise the last-seen timestamp store."""
        self._last_seen: dict[int, float] = {}
        self._rate = get_settings().throttle_rate

    def _prune(self, now: float) -> None:
        """Drop stale entries to keep the map small on a low-RAM VPS."""
        if len(self._last_seen) > _PRUNE_THRESHOLD:
            cutoff = now - 60
            self._last_seen = {
                uid: ts for uid, ts in self._last_seen.items() if ts > cutoff
            }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Allow or throttle the update based on the user's last activity."""
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last_seen.get(tg_user.id, 0.0)

        if now - last < self._rate:
            _log.info("throttled", telegram_id=tg_user.id)
            if isinstance(event, Message):
                await event.answer("Slow down a little, please.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Slow down a little, please.")
            return None

        self._last_seen[tg_user.id] = now
        self._prune(now)
        return await handler(event, data)
