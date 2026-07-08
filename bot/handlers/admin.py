"""/admin — administrative panel (admins only).

Provides a dashboard, user management (block / unblock / promote) and a view of
recent errors. Every handler here is gated behind :class:`RoleFilter`.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters import RoleFilter
from bot.models.user import User, UserRole
from bot.repositories import QueryRepository, UserRepository
from bot.services.osint_service import get_osint_service
from bot.utils import formatting

router = Router(name="admin")

# Gate the entire router: only admins may reach any handler here.
router.message.filter(RoleFilter(UserRole.ADMIN))


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    """Show the admin dashboard with core metrics."""
    users = UserRepository(session)
    queries = QueryRepository(session)
    cache = get_osint_service().cache

    lines = [
        formatting.bold("Admin dashboard"),
        "",
        formatting.kv("Total users", await users.count()),
        formatting.kv("Blocked users", await users.count_blocked()),
        formatting.kv("Total queries", await queries.total()),
        formatting.kv("Success rate", f"{await queries.success_rate() * 100:.1f}%"),
        formatting.kv("Cache entries", cache.size),
        formatting.kv("Cache hit rate", f"{cache.hit_rate * 100:.1f}%"),
        "",
        formatting.bold("Commands"),
        formatting.escape_md("/users — list recent users"),
        formatting.escape_md("/block <telegram_id> — block a user"),
        formatting.escape_md("/unblock <telegram_id> — unblock a user"),
        formatting.escape_md("/promote <telegram_id> — grant moderator"),
        formatting.escape_md("/demote <telegram_id> — revoke moderator"),
        formatting.escape_md("/errors — recent failed queries"),
    ]
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession) -> None:
    """List the most recently active users."""
    users = await UserRepository(session).list_users(limit=20)
    if not users:
        await message.answer("No users yet.")
        return

    lines = [formatting.bold("Recent users"), ""]
    for u in users:
        flags = []
        if u.is_blocked:
            flags.append("blocked")
        if u.role is not UserRole.USER:
            flags.append(u.role.value)
        suffix = f" ({', '.join(flags)})" if flags else ""
        handle = f"@{u.username}" if u.username else (u.full_name or "—")
        lines.append(
            f"• {formatting.code(u.telegram_id)} {formatting.escape_md(handle + suffix)}"
        )
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def _parse_target(command: CommandObject) -> int | None:
    """Parse a telegram id argument from a command, or ``None`` if invalid."""
    if not command.args:
        return None
    try:
        return int(command.args.strip().split()[0])
    except (ValueError, IndexError):
        return None


@router.message(Command("block"))
async def cmd_block(
    message: Message, command: CommandObject, session: AsyncSession, user: User
) -> None:
    """Block a user by Telegram id."""
    target = await _parse_target(command)
    if target is None:
        await message.answer("Usage: <code>/block &lt;telegram_id&gt;</code>")
        return
    if target == user.telegram_id:
        await message.answer("You cannot block yourself.")
        return
    ok = await UserRepository(session).set_blocked(target, True)
    await message.answer("User blocked." if ok else "User not found.")


@router.message(Command("unblock"))
async def cmd_unblock(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Unblock a user by Telegram id."""
    target = await _parse_target(command)
    if target is None:
        await message.answer("Usage: <code>/unblock &lt;telegram_id&gt;</code>")
        return
    ok = await UserRepository(session).set_blocked(target, False)
    await message.answer("User unblocked." if ok else "User not found.")


@router.message(Command("promote"))
async def cmd_promote(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Promote a user to moderator."""
    target = await _parse_target(command)
    if target is None:
        await message.answer("Usage: <code>/promote &lt;telegram_id&gt;</code>")
        return
    ok = await UserRepository(session).set_role(target, UserRole.MODERATOR)
    await message.answer("User promoted to moderator." if ok else "User not found.")


@router.message(Command("demote"))
async def cmd_demote(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Demote a moderator back to a regular user."""
    target = await _parse_target(command)
    if target is None:
        await message.answer("Usage: <code>/demote &lt;telegram_id&gt;</code>")
        return
    ok = await UserRepository(session).set_role(target, UserRole.USER)
    await message.answer("User demoted." if ok else "User not found.")


@router.message(Command("errors"))
async def cmd_errors(message: Message, session: AsyncSession) -> None:
    """Show the most recent failed queries for debugging."""
    errors = await QueryRepository(session).recent_errors(limit=10)
    if not errors:
        await message.answer("No recent errors. ✅")
        return

    lines = [formatting.bold("Recent errors"), ""]
    for entry in errors:
        when = entry.created_at.strftime("%Y-%m-%d %H:%M")
        reason = entry.error or "unknown"
        lines.append(
            f"⚠️ {formatting.code(entry.query)} "
            f"{formatting.escape_md(f'· {when} · {reason}')}"
        )
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)
