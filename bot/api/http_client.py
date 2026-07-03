"""Shared async HTTP client with connection pooling.

A single :class:`httpx.AsyncClient` is reused across all OSINT sources. Reusing
one client (with a bounded connection pool) is essential on a 1 GB RAM VPS —
it avoids per-request socket/TLS setup and keeps memory flat.
"""

from __future__ import annotations

from typing import Any

import httpx

from bot.config import get_settings
from bot.utils.logging import get_logger

_log = get_logger(__name__)
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared, lazily-created async HTTP client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout),
            headers={"User-Agent": settings.http_user_agent},
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=20, max_keepalive_connections=10
            ),
        )
    return _client


async def close_client() -> None:
    """Close the shared client on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """GET a URL and return parsed JSON, or ``None`` on any error.

    Errors are logged (not raised) so a single failing source never breaks the
    aggregated report.
    """
    client = get_client()
    try:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        _log.warning("http_get_failed", url=url, error=str(exc))
        return None
    except ValueError as exc:  # JSON decode error
        _log.warning("http_json_decode_failed", url=url, error=str(exc))
        return None


async def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> str | None:
    """GET a URL and return the response body as text, or ``None`` on error."""
    client = get_client()
    try:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        _log.warning("http_get_text_failed", url=url, error=str(exc))
        return None
