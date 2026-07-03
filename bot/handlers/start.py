"""/start, /help and /profile handlers plus main-menu navigation."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.callbacks import MenuCB
from bot.keyboards.inline import build_main_menu
from bot.models.user import User
from bot.repositories import FavoriteRepository, QueryRepository
from bot.utils import formatting

router = Router(name="start")


WELCOME = (
    "*OSINT Bot* — legal open\\-source intelligence\n\n"
    "Send me any of the following and I'll gather public information:\n"
    "• IP / IPv6 address\n"
    "• Domain / hostname\n"
    "• Email \\(your own, for breach checks\\)\n"
    "• Username\n"
    "• Company name\n"
    "• ASN, hash, URL\n\n"
    "_Only official APIs and public data are used\\. No leaked databases\\._"
)

HELP = (
    "*Commands*\n"
    "/start — main menu\n"
    "/help — this help\n"
    "/search `<query>` — auto\\-detect & search\n"
    "/ip `<address>` — investigate an IP\n"
    "/domain `<domain>` — investigate a domain\n"
    "/email `<email>` — breach check \\(own address\\)\n"
    "/company `<name>` — company / org lookup\n"
    "/history — your recent queries\n"
    "/favorite — your saved queries\n"
    "/settings — preferences\n"
    "/profile — your profile\n"
    "/stats — global statistics\n"
    "/admin — admin panel \\(admins only\\)\n\n"
    "_Tip: you can also just send a value without a command\\._"
)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Greet the user and show the main menu."""
    await message.answer(
        WELCOME,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=build_main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show the help text."""
    await message.answer(HELP, parse_mode=ParseMode.MARKDOWN_V2)


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession, user: User) -> None:
    """Show the user's profile and usage summary."""
    await _send_profile(message, session, user)


async def _send_profile(
    message: Message, session: AsyncSession, user: User
) -> None:
    """Render the profile card for a user."""
    history_count = await QueryRepository(session).history_count(user.id)
    fav_count = await FavoriteRepository(session).count(user.id)

    lines = [
        formatting.bold("Your profile"),
        formatting.kv("Name", user.full_name or "—"),
        formatting.kv("Username", f"@{user.username}" if user.username else "—"),
        formatting.kv("Role", user.role.value),
        formatting.kv("Total queries", user.total_queries),
        formatting.kv("History entries", history_count),
        formatting.kv("Favorites", fav_count),
        formatting.kv("Cache", "on" if user.use_cache else "off"),
        formatting.kv("Export format", user.export_format),
    ]
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


# ── Main-menu callback navigation ────────────────────────────────────────────
@router.callback_query(MenuCB.filter(F.action == "home"))
async def cb_home(query: CallbackQuery) -> None:
    """Return to the main menu."""
    if isinstance(query.message, Message):
        await query.message.answer(
            WELCOME,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_main_menu(),
        )
    await query.answer()


@router.callback_query(MenuCB.filter(F.action == "help"))
async def cb_help(query: CallbackQuery) -> None:
    """Show help from the menu."""
    if isinstance(query.message, Message):
        await query.message.answer(HELP, parse_mode=ParseMode.MARKDOWN_V2)
    await query.answer()


@router.callback_query(MenuCB.filter(F.action == "search"))
async def cb_search_prompt(query: CallbackQuery) -> None:
    """Prompt the user to type a query."""
    if isinstance(query.message, Message):
        await query.message.answer(
            formatting.escape_md("Send me a value to investigate:"),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    await query.answer()


@router.callback_query(MenuCB.filter(F.action == "profile"))
async def cb_profile(
    query: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Show the profile card from the menu."""
    if isinstance(query.message, Message):
        await _send_profile(query.message, session, user)
    await query.answer()
