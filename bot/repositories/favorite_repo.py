"""Favorites repository — add, list, remove bookmarked queries."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.favorite import Favorite


class FavoriteRepository:
    """Data-access object for user favorites."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind the repository to an active async session."""
        self._session = session

    async def add(
        self, user_id: int, query: str, query_type: str, note: str | None = None
    ) -> Favorite | None:
        """Add a favorite. Returns ``None`` if it already exists (unique)."""
        favorite = Favorite(
            user_id=user_id, query=query, query_type=query_type, note=note
        )
        self._session.add(favorite)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return None
        return favorite

    async def list(
        self, user_id: int, limit: int = 5, offset: int = 0
    ) -> list[Favorite]:
        """Return a page of a user's favorites (newest first)."""
        result = await self._session.execute(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self, user_id: int) -> int:
        """Return the number of favorites a user has."""
        result = await self._session.execute(
            select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
        )
        return int(result.scalar_one())

    async def get(self, favorite_id: int, user_id: int) -> Favorite | None:
        """Return a favorite by id, scoped to its owner."""
        result = await self._session.execute(
            select(Favorite).where(
                Favorite.id == favorite_id, Favorite.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def remove(self, favorite_id: int, user_id: int) -> bool:
        """Delete a favorite (scoped to owner). Returns ``True`` if removed."""
        result = await self._session.execute(
            delete(Favorite).where(
                Favorite.id == favorite_id, Favorite.user_id == user_id
            )
        )
        return result.rowcount > 0
