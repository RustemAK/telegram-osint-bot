"""Tiny async-safe TTL + LRU in-memory cache.

Deliberately dependency-free (no Redis) to keep the memory footprint minimal
on the target VPS. Entries expire after ``ttl`` seconds and the oldest entries
are evicted once ``max_size`` is exceeded.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """A bounded, time-aware cache safe for concurrent async access."""

    def __init__(self, ttl: int = 600, max_size: int = 512) -> None:
        """Initialise the cache.

        Args:
            ttl: Time-to-live for each entry, in seconds.
            max_size: Maximum number of entries kept before LRU eviction.
        """
        self._ttl = ttl
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any | None:
        """Return the cached value for ``key`` or ``None`` if missing/expired."""
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                self.misses += 1
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                # Expired — drop it.
                del self._store[key]
                self.misses += 1
                return None
            # Mark as recently used.
            self._store.move_to_end(key)
            self.hits += 1
            return value

    async def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` with the configured TTL."""
        async with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)
            self._store.move_to_end(key)
            # Evict the least-recently-used entries when over capacity.
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    async def clear(self) -> None:
        """Remove every entry from the cache."""
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        """Cache hit ratio in the range ``0.0``–``1.0``."""
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
