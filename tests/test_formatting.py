"""Tests for MarkdownV2 formatting helpers."""

from __future__ import annotations

from bot.utils import formatting


def test_escape_md_escapes_specials() -> None:
    assert formatting.escape_md("a.b-c!") == "a\\.b\\-c\\!"


def test_bold_and_code_wrap_and_escape() -> None:
    assert formatting.bold("x.y") == "*x\\.y*"
    assert formatting.code("1.2") == "`1\\.2`"


def test_format_result_renders_nested() -> None:
    out = formatting.format_result("Source", {"ip": "8.8.8.8", "tags": ["a", "b"]})
    assert "Source" in out
    assert "8\\.8\\.8\\.8" in out
    assert "•" in out  # list bullet


def test_truncate_message() -> None:
    long = "x" * 5000
    assert len(formatting.truncate_message(long)) <= 4000
