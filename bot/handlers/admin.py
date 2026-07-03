"""Admin panel: statistics, user management and error inspection.

Every handler here is guarded by :class:`RoleFilter` so only ADMIN users can
reach them. Moderators can view stats but not change roles.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.role_filter import RoleFilter
from bot.models.user import User, UserRole
from bot.repositories import QueryRepository, UserRepository
from bot.utils import formatting

router = Router(name="admin")

# Guard the whole router: message handlers require at least MODERATOR.
router.message.filter(RoleFilter(UserRole.MODERATOR))


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    """Show the admin dashboard with global statistics."""
    user_repo = UserRepository(session)
    query_repo = QueryRepository(session)

    total_users = await user_repo.count()
    blocked = await user_repo.count_blocked()
    total_queries = await query_repo.total()
    success_rate = await query_repo.success_rate()

    lines = [
        formatting.bold("Admin dashboard"),
        formatting.kv("Users", total_users),
        formatting.kv("Blocked", blocked),
        formatting.kv("Total queries", total_queries),
        formatting.kv("Success rate", f"{success_rate * 100:.1f}%"),
        "",
        formatting.escape_md("Commands:"),
        formatting.escape_md("/users — list recent users"),
        formatting.escape_md("/errors — recent failed queries"),
        formatting.escape_md("/promote <telegram_id> — grant moderator"),
        formatting.escape_md("/demote <telegram_id> — revoke to user"),
        formatting.escape_md("/block <telegram_id> — block a user"),
        formatting.escape_md("/unblock <telegram_id> — unblock a user"),
    ]
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession) -> None:
    """List the 20 most recently active users."""
    users = await UserRepository(session).list_users(limit=20)
    if not users:
        await message.answer("No users yet.")
        return

    lines = [formatting.bold("Recent users")]
    for u in users:
        flag = "🚫" if u.is_blocked else "•"
        handle = f"@{u.username}" if u.username else str(u.telegram_id)
        lines.append(
            f"{flag} {formatting.escape_md(handle)} "
            f"\\[{formatting.escape_md(u.role.value)}\\] "
            f"— {formatting.escape_md(u.total_queries)} queries "
            f"\\(id {formatting.code(u.telegram_id)}\\)"
        )
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


@router.message(Command("errors"))
async def cmd_errors(message: Message, session: AsyncSession) -> None:
    """Show the most recent failed queries for debugging."""
    errors = await QueryRepository(session).recent_errors(limit=10)
    if not errors:
        await message.answer("No recorded errors. 🎉")
        return

    lines = [formatting.bold("Recent errors")]
    for e in errors:
        lines.append(
            f"⚠️ {formatting.code(e.query)} — "
            f"{formatting.escape_md(e.error or 'unknown')}"
        )
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


# ── Role / block management (ADMIN only) ─────────────────────────────────────
def _parse_target_id(command: CommandObject) -> int | None:
    """Extract a numeric Telegram id from a command's arguments."""
    if not command.args:
        return None
    try:
        return int(command.args.strip().split()[0])
    except (ValueError, IndexError):
        return None


@router.message(Command("promote"), RoleFilter(UserRole.ADMIN))
async def cmd_promote(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Grant the MODERATOR role to a user by Telegram id."""
    target = _parse_target_id(command)
    if target is None:
        await message.answer("Usage: /promote <telegram_id>")
        return
    ok = await UserRepository(session).set_role(target, UserRole.MODERATOR)
    await message.answer("Promoted to moderator." if ok else "User not found.")


@router.message(Command("demote"), RoleFilter(UserRole.ADMIN))
async def cmd_demote(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Revoke privileges back to the USER role."""
    target = _parse_target_id(command)
    if target is None:
        await message.answer("Usage: /demote <telegram_id>")
        return
    ok = await UserRepository(session).set_role(target, UserRole.USER)
    await message.answer("Demoted to user." if ok else "User not found.")


@router.message(Command("block"), RoleFilter(UserRole.ADMIN))
async def cmd_block(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Block a user by Telegram id."""
    target = _parse_target_id(command)
    if target is None:
        await message.answer("Usage: /block <telegram_id>")
        return
    ok = await UserRepository(session).set_blocked(target, True)
    await message.answer("User blocked." if ok else "User not found.")


@router.message(Command("unblock"), RoleFilter(UserRole.ADMIN))
async def cmd_unblock(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Unblock a user by Telegram id."""
    target = _parse_target_id(command)
    if target is None:
        await message.answer("Usage: /unblock <telegram_id>")
        return
    ok = await UserRepository(session).set_blocked(target, False)
    await message.answer("User unblocked." if ok else "User not found.")
