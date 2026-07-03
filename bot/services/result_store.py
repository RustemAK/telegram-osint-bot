"""Short-lived store mapping compact tokens to full OSINT results.

Inline-button callback data is limited to 64 bytes, so full results cannot be
embedded. Instead we keep them briefly in memory under a short token and
reference that token from the buttons ("Details", "Export", "Favorite").
"""

from __future__ import annotations

import secrets

from bot.services.osint_service import OSINTResult
from bot.utils.cache import TTLCache


class ResultStore:
    """Token → :class:`OSINTResult` store backed by the TTL cache."""

    def __init__(self, ttl: int = 900, max_size: int = 256) -> None:
        """Initialise the underlying bounded cache."""
        self._cache = TTLCache(ttl=ttl, max_size=max_size)

    async def put(self, result: OSINTResult) -> str:
        """Store a result and return a short opaque token."""
        token = secrets.token_urlsafe(6)
        await self._cache.set(token, result)
        return token

    async def get(self, token: str) -> OSINTResult | None:
        """Retrieve a previously stored result by token (or ``None``)."""
        return await self._cache.get(token)


_store: ResultStore | None = None


def get_result_store() -> ResultStore:
    """Return the singleton :class:`ResultStore`."""
    global _store
    if _store is None:
        _store = ResultStore()
    return _store
