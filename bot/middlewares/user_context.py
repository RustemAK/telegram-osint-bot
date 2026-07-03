"""Middleware that registers/loads the user and enforces block status."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser

from bot.config import get_settings
from bot.repositories import UserRepository
from bot.utils.logging import get_logger

_log = get_logger(__name__, channel="audit")


class UserContextMiddleware(BaseMiddleware):
    """Ensure a :class:`~bot.models.user.User` exists and inject it.

    Also short-circuits updates from blocked users with a polite notice.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Load or create the DB user and attach it to the handler ``data``."""
        tg_user: TgUser | None = data.get("event_from_user")
        session = data.get("session")

        if tg_user is None or session is None:
            return await handler(event, data)

        settings = get_settings()
        repo = UserRepository(session)
        user, created = await repo.get_or_create(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            language_code=tg_user.language_code,
            admin_ids=settings.admin_ids,
        )

        if created:
            _log.info("user_registered", telegram_id=tg_user.id)

        if user.is_blocked:
            _log.warning("blocked_user_attempt", telegram_id=tg_user.id)
            text = "You have been blocked from using this bot."
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            return None

        data["user"] = user
        return await handler(event, data)
