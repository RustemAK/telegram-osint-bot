"""Role-based access-control filter.

Restricts a handler to users whose role is at least the required level. The
current :class:`~bot.models.user.User` is provided by
:class:`~bot.middlewares.user_context.UserContextMiddleware`.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from bot.models.user import User, UserRole

# Privilege ordering: higher number = more privileged.
_RANK: dict[UserRole, int] = {
    UserRole.USER: 1,
    UserRole.MODERATOR: 2,
    UserRole.ADMIN: 3,
}


class RoleFilter(BaseFilter):
    """Pass only when the current user meets the minimum required role."""

    def __init__(self, min_role: UserRole) -> None:
        """Store the minimum role required to pass this filter."""
        self.min_role = min_role

    async def __call__(self, event: TelegramObject, user: User | None = None) -> bool:
        """Return ``True`` if ``user`` has sufficient privileges."""
        if user is None:
            return False
        return _RANK.get(user.role, 0) >= _RANK[self.min_role]
