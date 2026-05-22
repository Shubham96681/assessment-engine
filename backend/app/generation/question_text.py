"""
Normalize question stems for UI and PDF — prompts use **OR** markdown but viewers are plain/HTML only.
"""
from __future__ import annotations

import re
from xml.sax.saxutils import escape

_BOLD_MD = re.compile(r"\*\*([^*]+)\*\*")

# ReportLab Helvetica lacks ⟂ ⊥ ∥ √ — use words / ASCII
_GEO_SYMBOLS: tuple[tuple[str, str], ...] = (
    ("\u27c2", " is perpendicular to "),  # ⟂
    ("\u22a5", " is perpendicular to "),  # ⊥
    ("\u2225", " is parallel to "),  # ∥
    ("\u2013", "-"),  # en-dash
    ("\u2014", "-"),  # em-dash
    ("\u2212", "-"),  # minus
    ("\u00b7", " x "),  # middle dot
    ("\u00d7", " x "),
    ("\u221a", " square root of "),  # √
    ("\u00b2", "^2"),
)


def normalize_geometry_symbols(text: str) -> str:
    """Replace Unicode math symbols with PDF-safe text."""
    if not text:
        return text
    out = text
    for src, dst in _GEO_SYMBOLS:
        out = out.replace(src, dst)
    # Close sqrt( if we opened it: sqrt(274 cm) stays readable
    return out


def strip_markdown_bold(text: str) -> str:
    """Plain text: **OR** → OR, geometry symbols → words."""
    if not text:
        return text
    return normalize_geometry_symbols(_BOLD_MD.sub(r"\1", text))


def to_reportlab_markup(text: str) -> str:
    """ReportLab Paragraph markup: **OR** → <b>OR</b>, XML-escaped elsewhere."""
    if not text:
        return text

    text = normalize_geometry_symbols(_BOLD_MD.sub(r"\1", text))

    parts: list[str] = []
    last = 0
    for m in _BOLD_MD.finditer(text):
        parts.append(escape(text[last : m.start()]))
        parts.append(f"<b>{escape(m.group(1))}</b>")
        last = m.end()
    parts.append(escape(text[last:]))
    return "".join(parts)
