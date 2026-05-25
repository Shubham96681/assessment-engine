"""
Register Unicode-capable TTF family for PDF math symbols (², √, ×, −).

Helvetica lacks these glyphs — they render as boxes or wrong letters (e.g. PR read as PB).
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional, Tuple

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

UNICODE_FONT = "AssessmentUnicode"
_registered = False


def _font_pairs() -> list[Tuple[str, str]]:
    """(registered_name, path) — normal + bold when available."""
    pairs: list[Tuple[str, str]] = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        fonts = os.path.join(windir, "Fonts")
        pairs.extend(
            [
                (UNICODE_FONT, os.path.join(fonts, "arial.ttf")),
                (f"{UNICODE_FONT}-Bold", os.path.join(fonts, "arialbd.ttf")),
                (UNICODE_FONT, os.path.join(fonts, "segoeui.ttf")),
                (f"{UNICODE_FONT}-Bold", os.path.join(fonts, "segoeuib.ttf")),
            ]
        )
    else:
        dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        dejavu_b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        pairs.extend(
            [
                (UNICODE_FONT, dejavu),
                (f"{UNICODE_FONT}-Bold", dejavu_b),
                (UNICODE_FONT, "/System/Library/Fonts/Supplemental/Arial.ttf"),
                (UNICODE_FONT, "/Library/Fonts/Arial.ttf"),
            ]
        )
    return pairs


def register_pdf_unicode_font() -> str:
    """Register AssessmentUnicode (+ Bold) if system TTFs exist; else Helvetica."""
    global _registered
    if _registered:
        return (
            UNICODE_FONT
            if UNICODE_FONT in pdfmetrics.getRegisteredFontNames()
            else "Helvetica"
        )

    _registered = True
    registered_normal: Optional[str] = None
    registered_bold: Optional[str] = None
    seen_paths: set[str] = set()

    for name, path in _font_pairs():
        if not os.path.isfile(path) or path in seen_paths:
            continue
        seen_paths.add(path)
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            if name == UNICODE_FONT:
                registered_normal = UNICODE_FONT
            elif name.endswith("-Bold"):
                registered_bold = name
        except Exception as exc:
            logger.warning("Could not register PDF font %s: %s", path, exc)

    if registered_normal:
        bold = registered_bold or registered_normal
        try:
            pdfmetrics.registerFontFamily(
                UNICODE_FONT,
                normal=registered_normal,
                bold=bold,
                italic=registered_normal,
                boldItalic=bold,
            )
        except Exception:
            pass
        logger.info("PDF Unicode font registered: %s", registered_normal)
        return UNICODE_FONT

    logger.warning("No Unicode TTF found — PDF math may show missing glyphs")
    return "Helvetica"


def pdf_body_font() -> str:
    return register_pdf_unicode_font()


def pdf_bold_font() -> str:
    register_pdf_unicode_font()
    bold = f"{UNICODE_FONT}-Bold"
    if bold in pdfmetrics.getRegisteredFontNames():
        return bold
    if UNICODE_FONT in pdfmetrics.getRegisteredFontNames():
        return UNICODE_FONT
    return "Helvetica-Bold"
