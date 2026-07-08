"""Application entry point.

Builds the :class:`~aiogram.Bot` and :class:`~aiogram.Dispatcher`, registers
middlewares and routers, initialises the database and starts long-polling.

Run with::

    python -m bot.main
"""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
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


# Commands shown in the Telegram "/" menu.
BOT_COMMANDS = [
    BotCommand(command="start", description="Main menu"),
    BotCommand(command="search", description="Auto-detect & investigate a value"),
    BotCommand(command="ip", description="Investigate an IP address"),
    BotCommand(command="domain", description="Investigate a domain"),
    BotCommand(command="email", description="Breach check (own address)"),
    BotCommand(command="company", description="Company / org lookup"),
    BotCommand(command="history", description="Your recent queries"),
    BotCommand(command="favorite", description="Your saved queries"),
    BotCommand(command="settings", description="Preferences"),
    BotCommand(command="profile", description="Your profile"),
    BotCommand(command="stats", description="Global statistics"),
    BotCommand(command="help", description="Help"),
]


def _register_middlewares(dp: Dispatcher) -> None:
    """Attach middlewares in the correct order for messages and callbacks.

    Order matters: logging (outermost) → throttling → DB session → user context
    (innermost, needs the session).
    """
    for observer in (dp.message, dp.callback_query):
        observer.middleware(LoggingMiddleware())
        observer.middleware(ThrottlingMiddleware())
        observer.middleware(DatabaseMiddleware())
        observer.middleware(UserContextMiddleware())


async def _on_startup(bot: Bot) -> None:
    """Bootstrap the database schema and publish the command list."""
    await init_models()
    await bot.set_my_commands(BOT_COMMANDS)
    me = await bot.get_me()
    _log.info("bot_started", username=me.username, id=me.id)


async def _on_shutdown() -> None:
    """Release the HTTP client and database engine cleanly."""
    await close_client()
    await dispose_engine()
    _log.info("bot_stopped")


async def main() -> None:
    """Configure, build and run the bot until interrupted."""
    settings = get_settings()
    configure_logging(level=settings.log_level, log_to_file=settings.log_to_file)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    _register_middlewares(dp)
    for router in get_routers():
        dp.include_router(router)

    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
