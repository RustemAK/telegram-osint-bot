"""aiogram routers grouped by feature.

The :func:`get_routers` helper returns all routers in include-order so the
dispatcher wires them up in one call.
"""

from aiogram import Router

from bot.handlers import (
    admin,
    common,
    favorites,
    history,
    search,
    settings as settings_handlers,
    start,
)


def get_routers() -> list[Router]:
    """Return every feature router in the correct include order."""
    return [
        start.router,
        search.router,
        history.router,
        favorites.router,
        settings_handlers.router,
        admin.router,
        common.router,  # catch-all last (free-text search)
    ]
