"""Query-history browsing, pagination and re-run."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.runner import run_search
from bot.keyboards.callbacks import HistoryCB, MenuCB, PageCB
from bot.keyboards.inline import build_history_row, build_pagination
from bot.models.user import User
from bot.utils import formatting
from bot.utils.validators import QueryType

router = Router(name="history")

_SCOPE = "history"


def _render_history(entries: list, page: int, total_pages: int) -> tuple[str, list]:
    """Build the history message text and the re-run button rows."""
    if not entries:
        return formatting.escape_md("You have no query history yet."), []

    lines = [formatting.bold("Your recent queries")]
    rows: list[list[InlineKeyboardButton]] = []
    for entry in entries:
        status = "✅" if entry.success else "⚠️"
        cache = "cached" if entry.cached else "live"
        lines.append(
            f"{status} {formatting.code(entry.query)} "
            f"— {formatting.escape_md(entry.query_type)} "
            f"\\({formatting.escape_md(cache)}\\)"
        )
        rows.append([build_history_row(entry.id)])
    return "\n".join(lines), rows


async def _show_history_page(
    message: Message, session: AsyncSession, user: User, page: int
) -> None:
    """Render a single page of the user's history."""
    from bot.repositories import QueryRepository

    repo = QueryRepository(session)
    total = await repo.history_count(user.id)
    page_size = user.page_size
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = max(0, min(page, total_pages - 1))

    entries = await repo.history(
        user.id, limit=page_size, offset=page * page_size
    )
    text, extra_rows = _render_history(entries, page, total_pages)
    keyboard = build_pagination(
        _SCOPE, page, total_pages, extra_rows=extra_rows
    )
    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@router.message(Command("history"))
async def cmd_history(message: Message, session: AsyncSession, user: User) -> None:
    """Show the first page of the user's query history."""
    await _show_history_page(message, session, user, 0)


@router.callback_query(MenuCB.filter(F.action == "history"))
async def cb_history_menu(
    query: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Show history from the main menu."""
    if isinstance(query.message, Message):
        await _show_history_page(query.message, session, user, 0)
    await query.answer()


@router.callback_query(PageCB.filter(F.scope == _SCOPE))
async def cb_history_page(
    query: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Navigate between history pages."""
    if isinstance(query.message, Message):
        await _show_history_page(query.message, session, user, callback_data.page)
    await query.answer()


@router.callback_query(HistoryCB.filter())
async def cb_history_rerun(
    query: CallbackQuery,
    callback_data: HistoryCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Re-run a query selected from history."""
    from bot.repositories import QueryRepository

    entries = await QueryRepository(session).history(user.id, limit=1000)
    entry = next((e for e in entries if e.id == callback_data.entry_id), None)
    if entry is None:
        await query.answer("Entry not found.", show_alert=True)
        return

    await query.answer("Re-running…")
    if isinstance(query.message, Message):
        forced = None
        try:
            forced = QueryType(entry.query_type)
        except ValueError:
            forced = None
        await run_search(
            query.message, session, user, entry.query, forced_type=forced
        )
