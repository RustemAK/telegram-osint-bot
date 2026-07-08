"""/favorite — save queries and browse / re-run / delete them."""

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


async def _render_favorites(
    session: AsyncSession, user: User, page: int
) -> tuple[str, list[list[InlineKeyboardButton]], int]:
    """Build favorites text, per-row delete buttons and total page count."""
    repo = FavoriteRepository(session)
    page_size = user.page_size
    total = await repo.count(user.id)
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = max(0, min(page, total_pages - 1))

    favorites = await repo.list(user.id, offset=page * page_size, limit=page_size)

    if not favorites:
        return (
            formatting.escape_md("No favorites yet. Run a search and tap ⭐ to save it."),
            [],
            total_pages,
        )

    lines = [formatting.bold("Your favorites"), ""]
    rows: list[list[InlineKeyboardButton]] = []
    for fav in favorites:
        lines.append(
            f"⭐ {formatting.code(fav.query)} "
            f"{formatting.escape_md(f'({fav.query_type})')}"
        )
        rows.append([build_favorite_delete_row(fav.id)])

    return "\n".join(lines), rows, total_pages


@router.message(Command("favorite", "favorites"))
async def cmd_favorites(message: Message, session: AsyncSession, user: User) -> None:
    """Show the first page of favorites."""
    text, rows, total_pages = await _render_favorites(session, user, 0)
    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=build_pagination("favorites", 0, total_pages, extra_rows=rows),
    )


@router.callback_query(MenuCB.filter(F.action == "favorites"))
async def cb_favorites(query: CallbackQuery, session: AsyncSession, user: User) -> None:
    """Open favorites from the menu."""
    if isinstance(query.message, Message):
        text, rows, total_pages = await _render_favorites(session, user, 0)
        await query.message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_pagination("favorites", 0, total_pages, extra_rows=rows),
        )
    await query.answer()


@router.callback_query(PageCB.filter(F.scope == "favorites"))
async def cb_favorites_page(
    query: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Paginate through favorites."""
    if isinstance(query.message, Message):
        text, rows, total_pages = await _render_favorites(session, user, callback_data.page)
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_pagination(
                "favorites", callback_data.page, total_pages, extra_rows=rows
            ),
        )
    await query.answer()


@router.callback_query(FavoriteCB.filter(F.action == "add"))
async def cb_favorite_add(
    query: CallbackQuery,
    callback_data: FavoriteCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Save the result referenced by a token as a favorite."""
    result = await get_result_store().get(callback_data.ref)
    if result is None:
        await query.answer("This result expired — run the search again.", show_alert=True)
        return
    created = await FavoriteRepository(session).add(
        user_id=user.id, query=result.query, query_type=result.query_type
    )
    if created is None:
        await query.answer("Already in your favorites.")
    else:
        await query.answer("Added to favorites ⭐")


@router.callback_query(FavoriteCB.filter(F.action == "del"))
async def cb_favorite_del(
    query: CallbackQuery,
    callback_data: FavoriteCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Delete a favorite by id (owner-scoped)."""
    try:
        favorite_id = int(callback_data.ref)
    except ValueError:
        await query.answer("Invalid favorite.", show_alert=True)
        return

    removed = await FavoriteRepository(session).remove(favorite_id, user.id)
    if not removed:
        await query.answer("Not found.", show_alert=True)
        return

    await query.answer("Removed.")
    if isinstance(query.message, Message):
        text, rows, total_pages = await _render_favorites(session, user, 0)
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_pagination("favorites", 0, total_pages, extra_rows=rows),
        )
