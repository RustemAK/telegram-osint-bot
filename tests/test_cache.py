"""Tests for the async TTL/LRU cache."""

from __future__ import annotations

import asyncio

import pytest

from bot.utils.cache import TTLCache


async def test_set_and_get() -> None:
    cache = TTLCache(ttl=10, max_size=10)
    await cache.set("k", 123)
    assert await cache.get("k") == 123
    assert cache.hits == 1


async def test_miss_returns_none() -> None:
    cache = TTLCache(ttl=10, max_size=10)
    assert await cache.get("absent") is None
    assert cache.misses == 1


async def test_expiry() -> None:
    cache = TTLCache(ttl=0, max_size=10)
    await cache.set("k", "v")
    await asyncio.sleep(0.01)
    assert await cache.get("k") is None


async def test_lru_eviction() -> None:
    cache = TTLCache(ttl=100, max_size=2)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.set("c", 3)  # should evict "a" (least recently used)
    assert await cache.get("a") is None
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3
    assert cache.size == 2


async def test_hit_rate() -> None:
    cache = TTLCache(ttl=100, max_size=10)
    await cache.set("k", 1)
    await cache.get("k")   # hit
    await cache.get("x")   # miss
    assert cache.hit_rate == pytest.approx(0.5)
