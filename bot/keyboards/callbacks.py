"""Typed callback-data factories (aiogram :class:`CallbackData`).

Using typed callbacks keeps inline-button payloads compact and unambiguous,
and lets handlers receive parsed, validated fields.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    """Main-menu navigation actions."""

    action: str  # e.g. "search", "history", "favorites", "settings", "help"


class ResultCB(CallbackData, prefix="res"):
    """Actions on a rendered OSINT result."""

    action: str  # "details" | "back"
    token: str  # short cache token referencing the stored result


class PageCB(CallbackData, prefix="pg"):
    """Pagination navigation for lists."""

    scope: str  # "history" | "favorites" | "users"
    page: int


class FavoriteCB(CallbackData, prefix="fav"):
    """Favorite add / remove actions."""

    action: str  # "add" | "del"
    ref: str  # query token (add) or favorite id (del)


class ExportCB(CallbackData, prefix="exp"):
    """Export a stored result to a file."""

    fmt: str  # "json" | "pdf"
    token: str


class HistoryCB(CallbackData, prefix="hist"):
    """Re-run a query from history."""

    entry_id: int


class SettingsCB(CallbackData, prefix="set"):
    """Change a user setting."""

    field: str  # "page_size" | "use_cache" | "export_format"
    value: str
