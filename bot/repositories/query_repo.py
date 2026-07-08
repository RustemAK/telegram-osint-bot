"""Query-history repository — logging, history retrieval and statistics."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.base import utcnow
from bot.models.query import QueryLog


class QueryRepository:
    """Data-access object for OSINT query logs."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind the repository to an active async session."""
        self._session = session

    async def add(
        self,
        *,
        user_id: int,
        query: str,
        query_type: str,
        cached: bool,
        success: bool,
        sources: list[str] | None,
        error: str | None,
        duration_ms: int,
    ) -> QueryLog:
        """Persist a new query-log entry."""
        entry = QueryLog(
            user_id=user_id,
            query=query,
            query_type=query_type,
            cached=cached,
            success=success,
            sources=",".join(sources) if sources else None,
            error=error,
            duration_ms=duration_ms,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get(self, entry_id: int) -> QueryLog | None:
        """Return a single query-log entry by id, or ``None``."""
        return await self._session.get(QueryLog, entry_id)

    async def history(
        self, user_id: int, limit: int = 5, offset: int = 0
    ) -> list[QueryLog]:
        """Return a page of a user's most recent queries."""
        result = await self._session.execute(
            select(QueryLog)
            .where(QueryLog.user_id == user_id)
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def history_count(self, user_id: int) -> int:
        """Return the total number of queries a user has made."""
        result = await self._session.execute(
            select(func.count(QueryLog.id)).where(QueryLog.user_id == user_id)
        )
        return int(result.scalar_one())

    async def count_since(self, user_id: int, hours: int = 24) -> int:
        """Count a user's queries in the last ``hours`` (for rate limiting)."""
        since = utcnow() - timedelta(hours=hours)
        result = await self._session.execute(
            select(func.count(QueryLog.id)).where(
                QueryLog.user_id == user_id, QueryLog.created_at >= since
            )
        )
        return int(result.scalar_one())

    async def total(self) -> int:
        """Return the global total number of queries."""
        result = await self._session.execute(select(func.count(QueryLog.id)))
        return int(result.scalar_one())

    async def popular(self, limit: int = 10) -> list[tuple[str, int]]:
        """Return the most frequently searched queries with counts."""
        result = await self._session.execute(
            select(QueryLog.query, func.count(QueryLog.id).label("cnt"))
            .group_by(QueryLog.query)
            .order_by(func.count(QueryLog.id).desc())
            .limit(limit)
        )
        return [(row[0], int(row[1])) for row in result.all()]

    async def recent_errors(self, limit: int = 10) -> list[QueryLog]:
        """Return the most recent failed queries for the admin error view."""
        result = await self._session.execute(
            select(QueryLog)
            .where(QueryLog.success.is_(False))
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def success_rate(self) -> float:
        """Return the global success ratio (0.0–1.0)."""
        total = await self.total()
        if total == 0:
            return 1.0
        result = await self._session.execute(
            select(func.count(QueryLog.id)).where(QueryLog.success.is_(True))
        )
        ok = int(result.scalar_one())
        return ok / total
