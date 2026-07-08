"""Cross-cutting handlers: /stats, result details/export callbacks and the
free-text catch-all that turns any plain message into a search."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.runner import run_search
from bot.keyboards.callbacks import ExportCB, ResultCB
from bot.models.user import User
from bot.repositories import QueryRepository, UserRepository
from bot.services.osint_service import get_osint_service
from bot.services.result_store import get_result_store
from bot.utils import export, formatting

router = Router(name="common")


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Show global, non-sensitive usage statistics."""
    users = UserRepository(session)
    queries = QueryRepository(session)
    cache = get_osint_service().cache

    total_users = await users.count()
    total_queries = await queries.total()
    success = await queries.success_rate()
    popular = await queries.popular(limit=5)

    lines = [
        formatting.bold("Global statistics"),
        "",
        formatting.kv("Users", total_users),
        formatting.kv("Queries", total_queries),
        formatting.kv("Success rate", f"{success * 100:.1f}%"),
        formatting.kv("Cache entries", cache.size),
        "",
        formatting.bold("Most searched"),
    ]
    if popular:
        for query_text, count in popular:
            lines.append(f"• {formatting.code(query_text)} — {formatting.escape_md(count)}")
    else:
        lines.append(formatting.escape_md("No queries yet."))

    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


@router.callback_query(ResultCB.filter(F.action == "details"))
async def cb_details(query: CallbackQuery, callback_data: ResultCB) -> None:
    """Send the full, untruncated report as a text block."""
    result = await get_result_store().get(callback_data.token)
    if result is None:
        await query.answer("This result expired — run the search again.", show_alert=True)
        return

    blocks = [formatting.format_summary(result.query, result.query_type, result.source_names)]
    for source in result.source_names:
        blocks.append("")
        blocks.append(formatting.format_result(source, result.results[source]))

    text = formatting.truncate_message("\n".join(blocks))
    if isinstance(query.message, Message):
        await query.message.answer(
            text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
        )
    await query.answer()


@router.callback_query(ExportCB.filter())
async def cb_export(query: CallbackQuery, callback_data: ExportCB) -> None:
    """Export a stored result to JSON or PDF and send it as a document."""
    result = await get_result_store().get(callback_data.token)
    if result is None:
        await query.answer("This result expired — run the search again.", show_alert=True)
        return

    await query.answer("Preparing file…")
    if callback_data.fmt == "pdf":
        document = export.to_pdf(result.query, result.results)
    else:
        document = export.to_json(result.query, result.results)

    if isinstance(query.message, Message):
        await query.message.answer_document(document)


@router.callback_query(F.data == "noop")
async def cb_noop(query: CallbackQuery) -> None:
    """Swallow taps on the non-interactive page indicator."""
    await query.answer()


@router.message(F.text & ~F.text.startswith("/"))
async def freeform_search(message: Message, session: AsyncSession, user: User) -> None:
    """Treat any plain text message as an auto-detected search."""
    await run_search(message, session, user, message.text)
