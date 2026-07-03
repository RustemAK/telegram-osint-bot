"""Inline keyboard builders.

All user-facing keyboards are assembled here so button layout & labels live in
one place. Pagination and result-action keyboards support the "Details",
"Back", "Next", "Export JSON/PDF", "Delete" and "Add to favorites" buttons.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import (
    ExportCB,
    FavoriteCB,
    HistoryCB,
    MenuCB,
    PageCB,
    ResultCB,
    SettingsCB,
)


def build_main_menu() -> InlineKeyboardMarkup:
    """Build the main menu shown by /start."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 New search", callback_data=MenuCB(action="search"))
    kb.button(text="🕘 History", callback_data=MenuCB(action="history"))
    kb.button(text="⭐ Favorites", callback_data=MenuCB(action="favorites"))
    kb.button(text="⚙️ Settings", callback_data=MenuCB(action="settings"))
    kb.button(text="👤 Profile", callback_data=MenuCB(action="profile"))
    kb.button(text="❓ Help", callback_data=MenuCB(action="help"))
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def build_result_keyboard(
    token: str, *, can_favorite: bool = True
) -> InlineKeyboardMarkup:
    """Build the action keyboard shown beneath an OSINT result."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Details", callback_data=ResultCB(action="details", token=token))
    if can_favorite:
        kb.button(text="⭐ Favorite", callback_data=FavoriteCB(action="add", ref=token))
    kb.button(text="📦 JSON", callback_data=ExportCB(fmt="json", token=token))
    kb.button(text="🧾 PDF", callback_data=ExportCB(fmt="pdf", token=token))
    kb.button(text="🏠 Menu", callback_data=MenuCB(action="home"))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def build_export_keyboard(token: str) -> InlineKeyboardMarkup:
    """Build a compact export-only keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Export JSON", callback_data=ExportCB(fmt="json", token=token))
    kb.button(text="🧾 Export PDF", callback_data=ExportCB(fmt="pdf", token=token))
    kb.adjust(2)
    return kb.as_markup()


def build_pagination(
    scope: str,
    page: int,
    total_pages: int,
    *,
    extra_rows: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    """Build a Prev / page-indicator / Next pagination row.

    Args:
        scope: Logical list scope ("history", "favorites", "users").
        page: Current zero-based page index.
        total_pages: Total number of pages.
        extra_rows: Optional additional button rows placed above the nav row.
    """
    kb = InlineKeyboardBuilder()

    if extra_rows:
        for row in extra_rows:
            kb.row(*row)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Back",
                callback_data=PageCB(scope=scope, page=page - 1).pack(),
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{max(total_pages, 1)}",
            callback_data="noop",
        )
    )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=PageCB(scope=scope, page=page + 1).pack(),
            )
        )
    kb.row(*nav)
    kb.row(
        InlineKeyboardButton(text="🏠 Menu", callback_data=MenuCB(action="home").pack())
    )
    return kb.as_markup()


def build_history_row(entry_id: int) -> InlineKeyboardButton:
    """Build a button that re-runs a query from history."""
    return InlineKeyboardButton(
        text="🔁 Re-run", callback_data=HistoryCB(entry_id=entry_id).pack()
    )


def build_favorite_delete_row(favorite_id: int) -> InlineKeyboardButton:
    """Build a button that deletes a favorite by id."""
    return InlineKeyboardButton(
        text="🗑 Delete",
        callback_data=FavoriteCB(action="del", ref=str(favorite_id)).pack(),
    )


def build_settings_keyboard(
    *, page_size: int, use_cache: bool, export_format: str
) -> InlineKeyboardMarkup:
    """Build the settings keyboard reflecting the user's current preferences."""
    kb = InlineKeyboardBuilder()

    # Page size options.
    for size in (3, 5, 10):
        mark = "•" if size == page_size else ""
        kb.button(
            text=f"{mark} Page {size}",
            callback_data=SettingsCB(field="page_size", value=str(size)),
        )

    # Cache toggle.
    kb.button(
        text=f"Cache: {'ON' if use_cache else 'OFF'}",
        callback_data=SettingsCB(
            field="use_cache", value="off" if use_cache else "on"
        ),
    )

    # Export format.
    for fmt in ("json", "pdf"):
        mark = "•" if fmt == export_format else ""
        kb.button(
            text=f"{mark} {fmt.upper()}",
            callback_data=SettingsCB(field="export_format", value=fmt),
        )

    kb.button(text="🏠 Menu", callback_data=MenuCB(action="home"))
    kb.adjust(3, 1, 2, 1)
    return kb.as_markup()
