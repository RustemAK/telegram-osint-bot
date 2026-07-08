"""Explicit search commands: /search, /ip, /domain, /email, /company.

These map user intent to the shared :func:`run_search` executor. Typed
commands (/ip, /domain, …) force the query type; /search auto-detects it.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.runner import run_search
from bot.models.user import User
from bot.utils.validators import QueryType

router = Router(name="search")


@router.message(Command("search"))
async def cmd_search(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Auto-detect the type of the supplied query and investigate it."""
    if not command.args:
        await message.answer("Usage: <code>/search &lt;value&gt;</code>")
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
        await message.answer("Usage: <code>/ip 8.8.8.8</code>")
        return
    await run_search(message, session, user, command.args, forced_type=QueryType.IP)


@router.message(Command("domain"))
async def cmd_domain(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
) -> None:
    """Investigate a domain / hostname."""
    if not command.args:
        await message.answer("Usage: <code>/domain example.com</code>")
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
    """Check an email address for public breach exposure (own address)."""
    if not command.args:
        await message.answer("Usage: <code>/email you@example.com</code>")
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
    """Look up a company / organisation across public sources."""
    if not command.args:
        await message.answer("Usage: <code>/company Vercel</code>")
        return
    await run_search(
        message, session, user, command.args, forced_type=QueryType.COMPANY
    )
