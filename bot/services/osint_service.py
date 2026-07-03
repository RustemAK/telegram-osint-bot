"""OSINT orchestration service.

Given a query and its detected type, this service:

* selects the relevant sources,
* runs them concurrently under a global semaphore (protects the 1 GB VPS),
* aggregates the results into a single dict,
* transparently caches results in memory.

Only legal / open sources are used. No leaked or stolen databases are queried.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from bot.api import (
    cert_source,
    dns_source,
    domain_source,
    ip_source,
    web_source,
    whois_source,
)
from bot.config import get_settings
from bot.utils.cache import TTLCache
from bot.utils.logging import get_logger
from bot.utils.validators import QueryType

_log = get_logger(__name__)

# Type alias for a source coroutine factory.
SourceCall = tuple[str, Callable[[str], Awaitable[dict[str, Any]]]]


@dataclass(slots=True)
class OSINTResult:
    """Aggregated result of an OSINT investigation."""

    query: str
    query_type: str
    cached: bool = False
    duration_ms: int = 0
    success: bool = True
    error: str | None = None
    results: dict[str, Any] = field(default_factory=dict)

    @property
    def source_names(self) -> list[str]:
        """Names of sources that returned actual (non-skipped) data."""
        return [
            name
            for name, data in self.results.items()
            if isinstance(data, dict) and "skipped" not in data
        ]


class OSINTService:
    """Runs OSINT lookups against many sources with bounded concurrency."""

    def __init__(self) -> None:
        """Initialise the shared cache and concurrency semaphore."""
        settings = get_settings()
        self._cache = TTLCache(
            ttl=settings.cache_ttl, max_size=settings.cache_max_size
        )
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)

    # ── Source selection ─────────────────────────────────────────────────────
    def _select_sources(self, qtype: QueryType) -> list[SourceCall]:
        """Return the list of ``(name, coroutine_factory)`` for a query type."""
        match qtype:
            case QueryType.IP | QueryType.IPV6:
                return [
                    ("Geolocation (ip-api)", ip_source.ip_api),
                    ("IPInfo", ip_source.ipinfo),
                    ("Reverse DNS", dns_source.reverse_dns),
                    ("RDAP", whois_source.rdap_ip),
                    ("AbuseIPDB", ip_source.abuseipdb),
                    ("GreyNoise", ip_source.greynoise),
                    ("Shodan", ip_source.shodan_host),
                    ("VirusTotal", domain_source.virustotal_ip),
                    ("Censys", domain_source.censys_host),
                ]
            case QueryType.DOMAIN | QueryType.HOSTNAME:
                return [
                    ("DNS", dns_source.dns_records),
                    ("RDAP", whois_source.rdap_domain),
                    ("WHOIS", whois_source.whois_domain),
                    ("Certificate Transparency", cert_source.crtsh),
                    ("VirusTotal", domain_source.virustotal_domain),
                    ("SecurityTrails", domain_source.securitytrails_domain),
                    ("Wikipedia", web_source.wikipedia_summary),
                ]
            case QueryType.EMAIL:
                return [
                    ("HIBP (own address)", web_source.hibp_breaches),
                    ("GitHub", web_source.github_search_code),
                ]
            case QueryType.USERNAME:
                return [
                    ("GitHub", web_source.github_user),
                    ("GitLab", web_source.gitlab_user),
                    ("Reddit", web_source.reddit_search),
                ]
            case QueryType.COMPANY:
                return [
                    ("Wikipedia", web_source.wikipedia_summary),
                    ("News", web_source.news),
                    ("Hacker News", web_source.hackernews),
                    ("GitHub", web_source.github_search_code),
                    ("Reddit", web_source.reddit_search),
                ]
            case QueryType.ASN:
                return [("RDAP", whois_source.rdap_ip)]
            case QueryType.HASH:
                return [("VirusTotal", domain_source.virustotal_hash)]
            case QueryType.URL:
                return [("VirusTotal", domain_source.virustotal_url)]
            case QueryType.SSL:
                return [("Certificate Transparency", cert_source.crtsh)]
            case _:
                # Free-text fallback → knowledge & social sources.
                return [
                    ("Wikipedia", web_source.wikipedia_summary),
                    ("Hacker News", web_source.hackernews),
                ]

    # ── Execution ────────────────────────────────────────────────────────────
    async def _run_source(
        self, name: str, func: Callable[[str], Awaitable[dict[str, Any]]], query: str
    ) -> tuple[str, dict[str, Any]]:
        """Execute a single source under the concurrency semaphore."""
        async with self._semaphore:
            try:
                data = await func(query)
                return name, data
            except Exception as exc:  # noqa: BLE001 - isolate per-source failures
                _log.warning("source_failed", source=name, error=str(exc))
                return name, {"skipped": f"error: {exc}"}

    async def investigate(
        self, query: str, qtype: QueryType, *, use_cache: bool = True
    ) -> OSINTResult:
        """Run all relevant sources for ``query`` and return aggregated data.

        Args:
            query: The sanitised query string.
            qtype: The detected query type.
            use_cache: Whether to read/write the in-memory result cache.
        """
        cache_key = f"{qtype.value}:{query.lower()}"

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                _log.info("cache_hit", query=query, type=qtype.value)
                cached.cached = True
                return cached

        start = time.monotonic()
        sources = self._select_sources(qtype)

        tasks = [self._run_source(name, func, query) for name, func in sources]
        gathered = await asyncio.gather(*tasks)

        results = {name: data for name, data in gathered}
        duration_ms = int((time.monotonic() - start) * 1000)

        result = OSINTResult(
            query=query,
            query_type=qtype.value,
            cached=False,
            duration_ms=duration_ms,
            success=True,
            results=results,
        )

        if use_cache:
            await self._cache.set(cache_key, result)

        _log.info(
            "investigation_done",
            query=query,
            type=qtype.value,
            sources=len(result.source_names),
            duration_ms=duration_ms,
        )
        return result

    @property
    def cache(self) -> TTLCache:
        """Expose the underlying cache (used by the /stats view)."""
        return self._cache


_service: OSINTService | None = None


def get_osint_service() -> OSINTService:
    """Return a lazily-created singleton :class:`OSINTService`."""
    global _service
    if _service is None:
        _service = OSINTService()
    return _service
