"""Favorites: add from a result, list with pagination, and delete."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.callbacks import FavoriteCB, MenuCB, PageCB
from bot.keyboards.inline import build_favorite_delete_row, build_pagination
from bot.models.user import User
from bot.repositories import FavoriteRepository
from bot.services.result_store import get_result_store
from bot.utils import formatting

router = Router(name="favorites")

_SCOPE = "favorites"


async def _show_favorites_page(
    message: Message, session: AsyncSession, user: User, page: int
) -> None:
    """Render a single page of the user's favorites."""
    repo = FavoriteRepository(session)
    total = await repo.count(user.id)
    page_size = user.page_size
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = max(0, min(page, total_pages - 1))

    favorites = await repo.list(
        user.id, limit=page_size, offset=page * page_size
    )

    if not favorites:
        await message.answer(
            formatting.escape_md("You have no favorites yet."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    lines = [formatting.bold("Your favorites")]
    rows: list[list[InlineKeyboardButton]] = []
    for fav in favorites:
        lines.append(
            f"⭐ {formatting.code(fav.query)} "
            f"— {formatting.escape_md(fav.query_type)}"
        )
        rows.append([build_favorite_delete_row(fav.id)])

    keyboard = build_pagination(_SCOPE, page, total_pages, extra_rows=rows)
    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@router.message(Command("favorite"))
async def cmd_favorites(message: Message, session: AsyncSession, user: User) -> None:
    """List the user's favorites."""
    await _show_favorites_page(message, session, user, 0)


@router.callback_query(MenuCB.filter(F.action == "favorites"))
async def cb_favorites_menu(
    query: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """List favorites from the main menu."""
    if isinstance(query.message, Message):
        await _show_favorites_page(query.message, session, user, 0)
    await query.answer()


@router.callback_query(PageCB.filter(F.scope == _SCOPE))
async def cb_favorites_page(
    query: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Navigate between favorites pages."""
    if isinstance(query.message, Message):
        await _show_favorites_page(query.message, session, user, callback_data.page)
    await query.answer()


@router.callback_query(FavoriteCB.filter(F.action == "add"))
async def cb_favorite_add(
    query: CallbackQuery,
    callback_data: FavoriteCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Add the referenced result's query to favorites."""
    result = await get_result_store().get(callback_data.ref)
    if result is None:
        await query.answer("This result has expired.", show_alert=True)
        return

    favorite = await FavoriteRepository(session).add(
        user.id, result.query, result.query_type
    )
    if favorite is None:
        await query.answer("Already in favorites.")
    else:
        await query.answer("Added to favorites.")


@router.callback_query(FavoriteCB.filter(F.action == "del"))
async def cb_favorite_del(
    query: CallbackQuery,
    callback_data: FavoriteCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Delete a favorite by id."""
    try:
        favorite_id = int(callback_data.ref)
    except ValueError:
        await query.answer("Invalid favorite.", show_alert=True)
        return

    removed = await FavoriteRepository(session).remove(favorite_id, user.id)
    if removed:
        await query.answer("Removed.")
        if isinstance(query.message, Message):
            await _show_favorites_page(query.message, session, user, 0)
    else:
        await query.answer("Not found.", show_alert=True)
