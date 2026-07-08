"""/history — browse recent queries with pagination and re-run."""

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
from bot.repositories import QueryRepository
from bot.utils import formatting

router = Router(name="history")


async def _render_history(
    session: AsyncSession, user: User, page: int
) -> tuple[str, list[list[InlineKeyboardButton]], int]:
    """Build the history text, per-row re-run buttons and total page count."""
    repo = QueryRepository(session)
    page_size = user.page_size
    total = await repo.history_count(user.id)
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = max(0, min(page, total_pages - 1))

    entries = await repo.history(user.id, offset=page * page_size, limit=page_size)

    if not entries:
        return formatting.escape_md("No queries yet. Send me something to investigate."), [], total_pages

    lines = [formatting.bold("Your recent queries"), ""]
    rows: list[list[InlineKeyboardButton]] = []
    for entry in entries:
        status = "✅" if entry.success else "⚠️"
        when = entry.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"{status} {formatting.code(entry.query)} "
            f"{formatting.escape_md(f'({entry.query_type}) · {when}')}"
        )
        rows.append([build_history_row(entry.id)])

    return "\n".join(lines), rows, total_pages


@router.message(Command("history"))
async def cmd_history(message: Message, session: AsyncSession, user: User) -> None:
    """Show the first page of query history."""
    text, rows, total_pages = await _render_history(session, user, 0)
    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=build_pagination("history", 0, total_pages, extra_rows=rows),
    )


@router.callback_query(MenuCB.filter(F.action == "history"))
async def cb_history(query: CallbackQuery, session: AsyncSession, user: User) -> None:
    """Open history from the main menu."""
    if isinstance(query.message, Message):
        text, rows, total_pages = await _render_history(session, user, 0)
        await query.message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_pagination("history", 0, total_pages, extra_rows=rows),
        )
    await query.answer()


@router.callback_query(PageCB.filter(F.scope == "history"))
async def cb_history_page(
    query: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Paginate through history."""
    if isinstance(query.message, Message):
        text, rows, total_pages = await _render_history(session, user, callback_data.page)
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_pagination(
                "history", callback_data.page, total_pages, extra_rows=rows
            ),
        )
    await query.answer()


@router.callback_query(HistoryCB.filter())
async def cb_history_rerun(
    query: CallbackQuery,
    callback_data: HistoryCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Re-run a query taken from history."""
    entry = await QueryRepository(session).get(callback_data.entry_id)
    if entry is None or entry.user_id != user.id:
        await query.answer("Entry not found.", show_alert=True)
        return
    await query.answer("Re-running…")
    if isinstance(query.message, Message):
        await run_search(query.message, session, user, entry.query)
