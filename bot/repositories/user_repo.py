"""User repository — CRUD and role management for :class:`User`."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.base import utcnow
from bot.models.user import User, UserRole


class UserRepository:
    """Data-access object for users."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind the repository to an active async session."""
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Return the user with the given Telegram id, or ``None``."""
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
        language_code: str | None = None,
        admin_ids: list[int] | None = None,
    ) -> tuple[User, bool]:
        """Return an existing user or create a new one.

        Args:
            telegram_id: The Telegram user id.
            username: Telegram @username.
            full_name: Display name.
            language_code: Telegram-provided language code.
            admin_ids: IDs that should be granted the ADMIN role on creation.

        Returns:
            A tuple ``(user, created)`` where ``created`` is ``True`` for a new
            registration.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            # Keep profile fields fresh and record activity.
            user.username = username or user.username
            user.full_name = full_name or user.full_name
            user.language_code = language_code or user.language_code
            user.last_seen_at = utcnow()
            return user, False

        role = (
            UserRole.ADMIN
            if admin_ids and telegram_id in admin_ids
            else UserRole.USER
        )
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language_code=language_code,
            role=role,
            last_seen_at=utcnow(),
        )
        self._session.add(user)
        await self._session.flush()
        return user, True

    async def set_role(self, telegram_id: int, role: UserRole) -> bool:
        """Update a user's role. Returns ``True`` if a user was updated."""
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        user.role = role
        return True

    async def set_blocked(self, telegram_id: int, blocked: bool) -> bool:
        """Block or unblock a user. Returns ``True`` if updated."""
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        user.is_blocked = blocked
        return True

    async def increment_queries(self, user: User) -> None:
        """Increment the user's lifetime query counter and touch last-seen."""
        user.total_queries += 1
        user.last_seen_at = utcnow()

    async def update_settings(self, user: User, **fields: object) -> None:
        """Apply a set of validated settings fields to a user."""
        allowed = {"page_size", "use_cache", "export_format"}
        for key, value in fields.items():
            if key in allowed:
                setattr(user, key, value)

    async def list_users(self, limit: int = 50, offset: int = 0) -> list[User]:
        """Return a page of users ordered by most recently seen."""
        result = await self._session.execute(
            select(User)
            .order_by(User.last_seen_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return the total number of registered users."""
        result = await self._session.execute(select(func.count(User.id)))
        return int(result.scalar_one())

    async def count_blocked(self) -> int:
        """Return the number of blocked users."""
        result = await self._session.execute(
            select(func.count(User.id)).where(User.is_blocked.is_(True))
        )
        return int(result.scalar_one())
