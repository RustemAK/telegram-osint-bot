"""Input validation & query-type detection.

Every user-supplied query is validated and classified here *before* any
network request is made. This is a first line of defence against malformed
input and injection attempts.
"""

from __future__ import annotations

import ipaddress
import re
from enum import Enum


class QueryType(str, Enum):
    """Supported OSINT query categories."""

    IP = "ip"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    HOSTNAME = "hostname"
    EMAIL = "email"
    USERNAME = "username"
    PHONE = "phone"
    COMPANY = "company"
    ASN = "asn"
    HASH = "hash"
    URL = "url"
    SSL = "ssl"
    UNKNOWN = "unknown"


# ── Regular expressions (compiled once) ──────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)([a-zA-Z0-9\-]{1,63}\.)+[a-zA-Z]{2,63}$"
)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_ASN_RE = re.compile(r"^AS\d{1,10}$", re.IGNORECASE)
_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{6,18}\d$")
_USERNAME_RE = re.compile(r"^@?[a-zA-Z0-9_]{2,32}$")
_HASH_RE = re.compile(r"^[a-fA-F0-9]{32,128}$")  # md5/sha1/sha256/sha512

MAX_QUERY_LENGTH = 256


def sanitize(query: str) -> str:
    """Trim and collapse whitespace, and clamp length.

    Note: SQL injection is prevented by using parameterised queries in the
    ORM layer — this helper only normalises user text.
    """
    cleaned = " ".join(query.strip().split())
    return cleaned[:MAX_QUERY_LENGTH]


def _is_ip(value: str) -> ipaddress._BaseAddress | None:
    """Return the parsed IP address object, or ``None`` if not an IP."""
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def detect_type(raw: str) -> QueryType:
    """Classify a sanitised query string into a :class:`QueryType`.

    The order of checks matters: the most specific / unambiguous patterns are
    tested first.
    """
    query = sanitize(raw)
    if not query:
        return QueryType.UNKNOWN

    # IP address (v4 / v6)
    ip = _is_ip(query)
    if ip is not None:
        return QueryType.IPV6 if ip.version == 6 else QueryType.IP

    # ASN (e.g. AS15169)
    if _ASN_RE.match(query):
        return QueryType.ASN

    # Cryptographic hash
    if _HASH_RE.match(query):
        return QueryType.HASH

    # URL
    if _URL_RE.match(query):
        return QueryType.URL

    # Email
    if _EMAIL_RE.match(query):
        return QueryType.EMAIL

    # Domain / hostname
    if _DOMAIN_RE.match(query):
        return QueryType.DOMAIN

    # Phone number
    if _PHONE_RE.match(query):
        return QueryType.PHONE

    # Username (@handle)
    if query.startswith("@") and _USERNAME_RE.match(query):
        return QueryType.USERNAME

    # Fallbacks: single token → username guess, otherwise company/free text.
    if " " not in query and _USERNAME_RE.match(query):
        return QueryType.USERNAME

    return QueryType.COMPANY


def is_valid(raw: str) -> bool:
    """Return ``True`` when the query is non-empty and within limits."""
    q = sanitize(raw)
    return bool(q) and len(q) <= MAX_QUERY_LENGTH
