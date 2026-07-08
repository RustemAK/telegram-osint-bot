"""Integration tests for the repositories against an in-memory SQLite DB."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.database.base import Base
from bot.models.user import UserRole
from bot.repositories import FavoriteRepository, QueryRepository, UserRepository


@pytest.fixture()
async def session() -> AsyncSession:
    """Provide a fresh in-memory database session for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_user_get_or_create_and_admin(session: AsyncSession) -> None:
    repo = UserRepository(session)
    user, created = await repo.get_or_create(111, username="a", admin_ids=[111])
    assert created is True
    assert user.role is UserRole.ADMIN

    same, created2 = await repo.get_or_create(111)
    assert created2 is False
    assert same.id == user.id


async def test_query_history_and_stats(session: AsyncSession) -> None:
    user, _ = await repo_user(session)
    queries = QueryRepository(session)

    await queries.add(
        user_id=user.id, query="example.com", query_type="domain",
        cached=False, success=True, sources=["DNS"], error=None, duration_ms=12,
    )
    await queries.add(
        user_id=user.id, query="8.8.8.8", query_type="ip",
        cached=False, success=False, sources=None, error="boom", duration_ms=5,
    )

    assert await queries.history_count(user.id) == 2
    assert await queries.total() == 2
    assert 0.0 <= await queries.success_rate() <= 1.0
    errors = await queries.recent_errors()
    assert errors and errors[0].error == "boom"


async def test_favorites_unique_and_remove(session: AsyncSession) -> None:
    user, _ = await repo_user(session)
    favorites = FavoriteRepository(session)

    first = await favorites.add(user.id, "example.com", "domain")
    assert first is not None
    duplicate = await favorites.add(user.id, "example.com", "domain")
    assert duplicate is None  # unique constraint

    assert await favorites.count(user.id) == 1
    removed = await favorites.remove(first.id, user.id)
    assert removed is True
    assert await favorites.count(user.id) == 0


async def repo_user(session: AsyncSession):
    """Helper: create and return a plain user."""
    return await UserRepository(session).get_or_create(222, username="u")
