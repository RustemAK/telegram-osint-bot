"""WHOIS and RDAP lookups (keyless).

RDAP is the modern, JSON-based successor to WHOIS and is preferred. Classic
WHOIS is offered as a fallback via the lightweight ``python-whois`` library,
executed in a thread to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from bot.api.http_client import get_json
from bot.utils.logging import get_logger

_log = get_logger(__name__)


async def rdap_domain(domain: str) -> dict[str, Any]:
    """Query the public RDAP bootstrap service for a domain."""
    data = await get_json(f"https://rdap.org/domain/{domain}")
    if not isinstance(data, dict):
        return {"skipped": "no RDAP data"}

    # Extract the most useful, compact fields.
    events = {
        e.get("eventAction"): e.get("eventDate")
        for e in data.get("events", [])
        if isinstance(e, dict)
    }
    return {
        "handle": data.get("handle"),
        "status": data.get("status", []),
        "registered": events.get("registration"),
        "expires": events.get("expiration"),
        "last_changed": events.get("last changed"),
        "nameservers": [
            ns.get("ldhName") for ns in data.get("nameservers", []) if isinstance(ns, dict)
        ],
    }


async def rdap_ip(ip: str) -> dict[str, Any]:
    """Query RDAP for IP allocation / network ownership information."""
    data = await get_json(f"https://rdap.org/ip/{ip}")
    if not isinstance(data, dict):
        return {"skipped": "no RDAP data"}
    return {
        "handle": data.get("handle"),
        "name": data.get("name"),
        "type": data.get("type"),
        "country": data.get("country"),
        "start_address": data.get("startAddress"),
        "end_address": data.get("endAddress"),
    }


def _whois_blocking(domain: str) -> dict[str, Any]:
    """Blocking WHOIS lookup executed in a worker thread."""
    try:
        import whois  # local import keeps startup light

        record = whois.whois(domain)
        data = dict(record) if record else {}
        # Reduce to compact, serialisable fields.
        return {
            "registrar": data.get("registrar"),
            "creation_date": str(data.get("creation_date")),
            "expiration_date": str(data.get("expiration_date")),
            "name_servers": data.get("name_servers"),
            "emails": data.get("emails"),
            "country": data.get("country"),
        }
    except Exception as exc:  # noqa: BLE001 - external lib may raise anything
        _log.info("whois_failed", domain=domain, error=str(exc))
        return {"skipped": "whois lookup failed"}


async def whois_domain(domain: str) -> dict[str, Any]:
    """Run a classic WHOIS lookup without blocking the event loop."""
    return await asyncio.to_thread(_whois_blocking, domain)
