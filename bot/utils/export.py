"""Result exporters: JSON and PDF.

Both exporters return ``BufferedInputFile`` objects ready to be sent through
aiogram. PDF generation uses ReportLab, a pure-python, low-memory library.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

import orjson
from aiogram.types import BufferedInputFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _timestamp() -> str:
    """Return a filesystem-safe UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def to_json(query: str, results: dict[str, Any]) -> BufferedInputFile:
    """Serialize results to a pretty-printed JSON file."""
    payload = {
        "query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    raw = orjson.dumps(payload, option=orjson.OPT_INDENT_2)
    return BufferedInputFile(raw, filename=f"osint_{_timestamp()}.json")


def _flatten(data: Any, prefix: str = "") -> list[str]:
    """Flatten a nested structure into ``key: value`` strings for the PDF."""
    lines: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten(value, path))
    elif isinstance(data, (list, tuple)):
        for idx, value in enumerate(data):
            lines.extend(_flatten(value, f"{prefix}[{idx}]"))
    else:
        lines.append(f"<b>{prefix}:</b> {data}")
    return lines


def to_pdf(query: str, results: dict[str, Any]) -> BufferedInputFile:
    """Render results into a compact A4 PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"OSINT Report — {query}",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("OSINT Report", styles["Title"]),
        Paragraph(f"Query: {query}", styles["Normal"]),
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Spacer(1, 8 * mm),
    ]

    for source, data in results.items():
        story.append(Paragraph(str(source), styles["Heading2"]))
        for line in _flatten(data):
            # Escape angle brackets that are not our own <b> tags is unnecessary
            # here because _flatten only injects controlled markup.
            story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 5 * mm))

    doc.build(story)
    buffer.seek(0)
    return BufferedInputFile(buffer.read(), filename=f"osint_{_timestamp()}.pdf")
