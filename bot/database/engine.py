"""Async SQLAlchemy engine & session management.

A single engine is created at startup with a small connection pool sized for a
1 GB RAM VPS. SQLite uses ``NullPool`` (it does not benefit from pooling),
whereas PostgreSQL gets a modest ``QueuePool``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from bot.config import get_settings
from bot.database.base import Base

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> AsyncEngine:
    """Create (once) and return the global async engine."""
    global _engine, _sessionmaker
    if _engine is not None:
        return _engine

    settings = get_settings()

    if settings.is_sqlite:
        # SQLite: no real pooling; keep it simple and memory-light.
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            poolclass=NullPool,
            connect_args={"timeout": 30},
        )
    else:
        # PostgreSQL: small pool tuned for a constrained VPS.
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

    _sessionmaker = async_sessionmaker(
        bind=_engine, expire_on_commit=False, class_=AsyncSession
    )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the configured session factory, initialising it if needed."""
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None  # for type-checkers
    return _sessionmaker


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a transactional session, committing on success.

    Usage::

        async with get_session() as session:
            ...
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models() -> None:
    """Create all tables. Used for SQLite / first-run bootstrap.

    For PostgreSQL in production, prefer Alembic migrations.
    """
    engine = init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the engine and its connections on shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
