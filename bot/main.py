"""Application entrypoint.

Wires together the aiogram :class:`Bot` and :class:`Dispatcher`, registers
middlewares and routers, sets the command menu, and runs long polling with
graceful startup/shutdown of shared resources (DB engine + HTTP client).
"""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.api.http_client import close_client
from bot.config import get_settings
from bot.database import dispose_engine, init_models
from bot.handlers import get_routers
from bot.middlewares import (
    DatabaseMiddleware,
    LoggingMiddleware,
    ThrottlingMiddleware,
    UserContextMiddleware,
)
from bot.utils.logging import configure_logging, get_logger

_log = get_logger(__name__)


# Public command menu shown in the Telegram UI.
_COMMANDS = [
    BotCommand(command="start", description="Main menu"),
    BotCommand(command="help", description="How to use the bot"),
    BotCommand(command="search", description="Auto-detect & investigate"),
    BotCommand(command="ip", description="Investigate an IP address"),
    BotCommand(command="domain", description="Investigate a domain"),
    BotCommand(command="email", description="Breach check (own address)"),
    BotCommand(command="company", description="Company / org lookup"),
    BotCommand(command="history", description="Your recent queries"),
    BotCommand(command="favorite", description="Your saved queries"),
    BotCommand(command="settings", description="Preferences"),
    BotCommand(command="profile", description="Your profile"),
    BotCommand(command="stats", description="Global statistics"),
]


def _register_middlewares(dp: Dispatcher) -> None:
    """Register middlewares in outer→inner order for messages & callbacks.

    Order matters: logging (outermost) → throttling → database → user context.
    The DB session must exist before the user-context middleware loads the user.
    """
    for observer in (dp.message, dp.callback_query):
        observer.middleware(LoggingMiddleware())
        observer.middleware(ThrottlingMiddleware())
        observer.middleware(DatabaseMiddleware())
        observer.middleware(UserContextMiddleware())


async def _on_startup(bot: Bot) -> None:
    """Initialise database tables and publish the command menu."""
    settings = get_settings()
    if settings.is_sqlite:
        # For SQLite we bootstrap tables directly; Postgres uses Alembic.
        await init_models()
    await bot.set_my_commands(_COMMANDS)
    _log.info("startup_complete", admins=len(settings.admin_ids))


async def _on_shutdown() -> None:
    """Dispose of the DB engine and close the shared HTTP client."""
    await close_client()
    await dispose_engine()
    _log.info("shutdown_complete")


async def main() -> None:
    """Configure and run the bot until interrupted."""
    settings = get_settings()
    configure_logging(level=settings.log_level, log_to_file=settings.log_to_file)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    _register_middlewares(dp)
    for router in get_routers():
        dp.include_router(router)

    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)

    _log.info("bot_starting")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


def run() -> None:
    """Synchronous console-script entrypoint."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    run()
