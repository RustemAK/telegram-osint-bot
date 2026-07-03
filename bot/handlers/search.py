"""Search commands and result-action callbacks.

Covers the explicit search commands (/search, /ip, /domain, /email, /company)
and the inline actions rendered beneath a result: Details, Export (JSON/PDF).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.runner import run_search
from bot.keyboards.callbacks import ExportCB, ResultCB
from bot.keyboards.inline import build_result_keyboard
from bot.models.user import User
from bot.services.result_store import get_result_store
from bot.utils import export, formatting
from bot.utils.validators import QueryType

router = Router(name="search")


def _needs_argument(qtype_label: str) -> str:
    """Return a friendly usage hint for a command missing its argument."""
    return formatting.escape_md(f"Usage: provide a {qtype_label} after the command.")


@router.message(Command("search"))
async def cmd_search(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Auto-detect and investigate the supplied query."""
    if not command.args:
        await message.answer(
            _needs_argument("query"), parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    await run_search(message, session, user, command.args)


@router.message(Command("ip"))
async def cmd_ip(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Investigate an IP address."""
    if not command.args:
        await message.answer(
            _needs_argument("IP address"), parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    await run_search(message, session, user, command.args, forced_type=QueryType.IP)


@router.message(Command("domain"))
async def cmd_domain(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Investigate a domain."""
    if not command.args:
        await message.answer(
            _needs_argument("domain"), parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    await run_search(
        message, session, user, command.args, forced_type=QueryType.DOMAIN
    )


@router.message(Command("email"))
async def cmd_email(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Run a breach check for an email address (own address only)."""
    if not command.args:
        await message.answer(
            _needs_argument("email address"), parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    await run_search(
        message, session, user, command.args, forced_type=QueryType.EMAIL
    )


@router.message(Command("company"))
async def cmd_company(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Investigate a company / organisation name."""
    if not command.args:
        await message.answer(
            _needs_argument("company name"), parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    await run_search(
        message, session, user, command.args, forced_type=QueryType.COMPANY
    )


# ── Result-action callbacks ──────────────────────────────────────────────────
@router.callback_query(ResultCB.filter(F.action == "details"))
async def cb_details(query: CallbackQuery, callback_data: ResultCB) -> None:
    """Show the full, untruncated per-source breakdown for a result."""
    result = await get_result_store().get(callback_data.token)
    if result is None:
        await query.answer("This result has expired. Please search again.", show_alert=True)
        return

    blocks = [formatting.bold(f"Full report — {result.query}")]
    for source in result.source_names:
        blocks.append("")
        blocks.append(formatting.format_result(source, result.results[source]))

    text = formatting.truncate_message("\n".join(blocks))
    if isinstance(query.message, Message):
        await query.message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_result_keyboard(callback_data.token),
            disable_web_page_preview=True,
        )
    await query.answer()


@router.callback_query(ExportCB.filter())
async def cb_export(query: CallbackQuery, callback_data: ExportCB) -> None:
    """Export a stored result to JSON or PDF and send it as a document."""
    result = await get_result_store().get(callback_data.token)
    if result is None:
        await query.answer("This result has expired. Please search again.", show_alert=True)
        return

    if callback_data.fmt == "pdf":
        document = export.to_pdf(result.query, result.results)
    else:
        document = export.to_json(result.query, result.results)

    if isinstance(query.message, Message):
        await query.message.answer_document(document)
    await query.answer("Export ready.")
