"""Tests for query-type detection and sanitisation."""

from __future__ import annotations

import pytest

from bot.utils.validators import QueryType, detect_type, is_valid, sanitize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("8.8.8.8", QueryType.IP),
        ("1.1.1.1", QueryType.IP),
        ("2001:4860:4860::8888", QueryType.IPV6),
        ("example.com", QueryType.DOMAIN),
        ("sub.example.co.uk", QueryType.DOMAIN),
        ("user@example.com", QueryType.EMAIL),
        ("https://vercel.com/docs", QueryType.URL),
        ("AS15169", QueryType.ASN),
        ("@johndoe", QueryType.USERNAME),
        ("johndoe", QueryType.USERNAME),
        ("d41d8cd98f00b204e9800998ecf8427e", QueryType.HASH),
        ("Acme Corporation", QueryType.COMPANY),
    ],
)
def test_detect_type(raw: str, expected: QueryType) -> None:
    assert detect_type(raw) is expected


def test_sanitize_collapses_whitespace_and_clamps() -> None:
    assert sanitize("  hello   world  ") == "hello world"
    assert len(sanitize("a" * 500)) == 256


def test_is_valid() -> None:
    assert is_valid("example.com")
    assert not is_valid("   ")
    assert not is_valid("")
