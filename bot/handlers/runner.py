"""Shared search execution used by several handlers.

Centralises the full lifecycle of a query: validation, rate-limit check,
running the OSINT service, persisting the log, storing the result for callbacks
and rendering the reply. Keeping this in one place avoids duplication across
/search, /ip, /domain, /email and history re-runs.
"""

from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.inline import build_result_keyboard
from bot.models.user import User
from bot.repositories import QueryRepository, UserRepository
from bot.services.osint_service import get_osint_service
from bot.services.result_store import get_result_store
from bot.utils import formatting
from bot.utils.logging import get_logger
from bot.utils.validators import QueryType, detect_type, is_valid, sanitize

_log = get_logger(__name__)


async def run_search(
    message: Message,
    session: AsyncSession,
    user: User,
    raw_query: str,
    *,
    forced_type: QueryType | None = None,
) -> None:
    """Execute an OSINT search and reply with a formatted report.

    Args:
        message: The message to reply to.
        session: Active DB session (from middleware).
        user: The current user.
        raw_query: The user-supplied query text.
        forced_type: Optional type override (used by /ip, /domain, /email).
    """
    settings = get_settings()
    query = sanitize(raw_query)

    if not is_valid(query):
        await message.answer("Please provide a valid, non-empty query.")
        return

    # ── Daily rate limit ─────────────────────────────────────────────────────
    query_repo = QueryRepository(session)
    if settings.daily_query_limit > 0:
        used = await query_repo.count_since(user.id, hours=24)
        if used >= settings.daily_query_limit:
            await message.answer(
                "You have reached your daily query limit. Try again tomorrow."
            )
            _log.warning("rate_limited", user_id=user.id, used=used)
            return

    qtype = forced_type or detect_type(query)

    status = await message.answer(
        formatting.escape_md(f"Investigating '{query}' as {qtype.value}…"),
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    service = get_osint_service()
    result = await service.investigate(query, qtype, use_cache=user.use_cache)

    # ── Persist history & counters ───────────────────────────────────────────
    await query_repo.add(
        user_id=user.id,
        query=query,
        query_type=qtype.value,
        cached=result.cached,
        success=result.success,
        sources=result.source_names,
        error=result.error,
        duration_ms=result.duration_ms,
    )
    await UserRepository(session).increment_queries(user)

    # ── Store for callback actions (details / export / favorite) ─────────────
    token = await get_result_store().put(result)

    # ── Render ───────────────────────────────────────────────────────────────
    header = formatting.format_summary(query, qtype.value, result.source_names)
    cache_line = formatting.escape_md(
        f"cached • {result.duration_ms} ms"
        if result.cached
        else f"live • {result.duration_ms} ms"
    )

    blocks = [header, f"_{cache_line}_"]
    for source in result.source_names:
        blocks.append("")
        blocks.append(formatting.format_result(source, result.results[source]))

    if not result.source_names:
        blocks.append("")
        blocks.append(formatting.escape_md("No open-source data found."))

    text = formatting.truncate_message("\n".join(blocks))

    await status.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=build_result_keyboard(token),
        disable_web_page_preview=True,
    )
