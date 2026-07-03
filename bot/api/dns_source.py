"""DNS & Reverse-DNS lookups (keyless).

Uses :mod:`dnspython` in async resolver mode. All lookups are wrapped so a
missing record type simply yields an empty list rather than an error.
"""

from __future__ import annotations

from typing import Any

import dns.asyncresolver
import dns.reversename
from dns.exception import DNSException

from bot.utils.logging import get_logger

_log = get_logger(__name__)

_RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA")


async def dns_records(domain: str) -> dict[str, Any]:
    """Resolve common DNS record types for a domain.

    Returns a mapping of record-type → list of string values. Record types with
    no answer are omitted.
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = 8.0
    records: dict[str, list[str]] = {}

    for rtype in _RECORD_TYPES:
        try:
            answers = await resolver.resolve(domain, rtype)
            records[rtype] = [str(rdata).strip() for rdata in answers]
        except DNSException:
            continue  # No such record / timeout — skip quietly.

    if not records:
        return {"skipped": "no DNS records resolved"}
    return records


async def reverse_dns(ip: str) -> dict[str, Any]:
    """Perform a reverse DNS (PTR) lookup for an IP address."""
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = 8.0
    try:
        rev_name = dns.reversename.from_address(ip)
        answers = await resolver.resolve(rev_name, "PTR")
        return {"ptr": [str(r).strip() for r in answers]}
    except DNSException as exc:
        _log.info("reverse_dns_empty", ip=ip, error=str(exc))
        return {"ptr": []}
