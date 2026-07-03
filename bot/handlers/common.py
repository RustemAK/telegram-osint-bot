"""Global /stats plus the free-text catch-all search handler.

This router is included last so its catch-all message handler only fires when
no command or more specific handler matched. Plain text sent by a user is
treated as an OSINT query.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.runner import run_search
from bot.models.user import User
from bot.repositories import QueryRepository, UserRepository
from bot.services.osint_service import get_osint_service
from bot.utils import formatting

router = Router(name="common")


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Show public, global usage statistics."""
    user_repo = UserRepository(session)
    query_repo = QueryRepository(session)

    total_users = await user_repo.count()
    total_queries = await query_repo.total()
    success_rate = await query_repo.success_rate()
    popular = await query_repo.popular(limit=5)
    cache_size = get_osint_service().cache.size

    lines = [
        formatting.bold("Global statistics"),
        formatting.kv("Users", total_users),
        formatting.kv("Queries", total_queries),
        formatting.kv("Success rate", f"{success_rate * 100:.1f}%"),
        formatting.kv("Cached results", cache_size),
    ]
    if popular:
        lines.append("")
        lines.append(formatting.bold("Most searched"))
        for query_text, count in popular:
            lines.append(
                f"• {formatting.code(query_text)} "
                f"— {formatting.escape_md(count)}"
            )

    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


@router.message(F.text & ~F.text.startswith("/"))
async def free_text_search(
    message: Message, session: AsyncSession, user: User
) -> None:
    """Treat any non-command text message as an auto-detected OSINT query."""
    await run_search(message, session, user, message.text or "")
