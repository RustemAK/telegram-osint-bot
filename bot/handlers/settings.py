"""/settings — per-user preferences (page size, cache, export format)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.callbacks import MenuCB, SettingsCB
from bot.keyboards.inline import build_settings_keyboard
from bot.models.user import User
from bot.repositories import UserRepository
from bot.utils import formatting

router = Router(name="settings")


def _settings_text(user: User) -> str:
    """Render the settings summary card."""
    return "\n".join(
        [
            formatting.bold("Settings"),
            "",
            formatting.kv("Results per page", user.page_size),
            formatting.kv("Cache", "on" if user.use_cache else "off"),
            formatting.kv("Export format", user.export_format.upper()),
            "",
            formatting.escape_md("Tap a button below to change a preference."),
        ]
    )


def _keyboard(user: User):
    """Build the settings keyboard from the user's current preferences."""
    return build_settings_keyboard(
        page_size=user.page_size,
        use_cache=user.use_cache,
        export_format=user.export_format,
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, user: User) -> None:
    """Show the settings panel."""
    await message.answer(
        _settings_text(user),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_keyboard(user),
    )


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def cb_settings(query: CallbackQuery, user: User) -> None:
    """Open the settings panel from the menu."""
    if isinstance(query.message, Message):
        await query.message.answer(
            _settings_text(user),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_keyboard(user),
        )
    await query.answer()


@router.callback_query(SettingsCB.filter())
async def cb_update_setting(
    query: CallbackQuery,
    callback_data: SettingsCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Apply a settings change and refresh the panel."""
    repo = UserRepository(session)

    if callback_data.field == "page_size":
        try:
            size = int(callback_data.value)
        except ValueError:
            await query.answer("Invalid value.", show_alert=True)
            return
        if size not in (3, 5, 10):
            await query.answer("Unsupported page size.", show_alert=True)
            return
        await repo.update_settings(user, page_size=size)

    elif callback_data.field == "use_cache":
        await repo.update_settings(user, use_cache=callback_data.value == "on")

    elif callback_data.field == "export_format":
        if callback_data.value not in ("json", "pdf"):
            await query.answer("Unsupported format.", show_alert=True)
            return
        await repo.update_settings(user, export_format=callback_data.value)

    else:
        await query.answer("Unknown setting.", show_alert=True)
        return

    await query.answer("Saved ✅")
    if isinstance(query.message, Message):
        await query.message.edit_text(
            _settings_text(user),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_keyboard(user),
        )
