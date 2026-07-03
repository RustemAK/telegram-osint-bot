"""MarkdownV2 formatting helpers for Telegram messages.

Telegram's MarkdownV2 requires a fixed set of characters to be escaped. These
helpers build safe, well-formatted messages from OSINT result dictionaries.
"""

from __future__ import annotations

from typing import Any

# Characters that MUST be escaped in Telegram MarkdownV2.
_MDV2_SPECIALS = r"_*[]()~`>#+-=|{}.!"


def escape_md(text: Any) -> str:
    """Escape a value for safe inclusion in a MarkdownV2 message."""
    s = str(text)
    return "".join(f"\\{ch}" if ch in _MDV2_SPECIALS else ch for ch in s)


def bold(text: Any) -> str:
    """Return ``text`` wrapped in MarkdownV2 bold markers (escaped inside)."""
    return f"*{escape_md(text)}*"


def code(text: Any) -> str:
    """Return ``text`` as an inline code span (escaped inside)."""
    return f"`{escape_md(text)}`"


def kv(label: str, value: Any) -> str:
    """Format a ``label: value`` line with a bold label."""
    return f"{bold(label)}: {escape_md(value)}"


def _render_value(value: Any, indent: int = 0) -> list[str]:
    """Recursively render nested dict/list structures into MarkdownV2 lines."""
    pad = "  " * indent
    lines: list[str] = []

    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(val, (dict, list)):
                lines.append(f"{pad}{bold(key)}:")
                lines.extend(_render_value(val, indent + 1))
            else:
                lines.append(f"{pad}{kv(str(key), val)}")
    elif isinstance(value, (list, tuple)):
        for item in value[:25]:  # cap list length for readability / size
            if isinstance(item, (dict, list)):
                lines.extend(_render_value(item, indent))
            else:
                lines.append(f"{pad}• {escape_md(item)}")
        if len(value) > 25:
            lines.append(f"{pad}{escape_md(f'… and {len(value) - 25} more')}")
    else:
        lines.append(f"{pad}{escape_md(value)}")

    return lines


def format_result(source: str, data: dict[str, Any]) -> str:
    """Render a single source's result dictionary as a MarkdownV2 block."""
    header = f"🔎 {bold(source)}"
    body = _render_value(data)
    return "\n".join([header, *body])


def format_summary(query: str, query_type: str, sources: list[str]) -> str:
    """Build the header shown above aggregated OSINT results."""
    return "\n".join(
        [
            bold("OSINT Report"),
            kv("Query", query),
            kv("Type", query_type),
            kv("Sources", ", ".join(sources) if sources else "none"),
        ]
    )


def truncate_message(text: str, limit: int = 4000) -> str:
    """Ensure a message stays within Telegram's 4096-char limit."""
    if len(text) <= limit:
        return text
    return text[: limit - 20] + escape_md("\n… (truncated)")
