"""
Register a Unicode-capable TTF for PDF math symbols (², √, ×, −).

Helvetica lacks these glyphs — they render as boxes or wrong letters (e.g. PR read as PB).
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

UNICODE_FONT = "AssessmentUnicode"
_registered = False


def _font_candidates() -> list[str]:
    paths: list[str] = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        fonts = os.path.join(windir, "Fonts")
        paths.extend(
            [
                os.path.join(fonts, "arial.ttf"),
                os.path.join(fonts, "segoeui.ttf"),
                os.path.join(fonts, "calibri.ttf"),
            ]
        )
    else:
        paths.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
        )
    return paths


def register_pdf_unicode_font() -> str:
    """Register AssessmentUnicode if a system TTF is available; else Helvetica."""
    global _registered
    if _registered:
        return (
            UNICODE_FONT
            if UNICODE_FONT in pdfmetrics.getRegisteredFontNames()
            else "Helvetica"
        )

    _registered = True
    for path in _font_candidates():
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont(UNICODE_FONT, path))
                logger.info("PDF Unicode font registered from %s", path)
                return UNICODE_FONT
            except Exception as exc:
                logger.warning("Could not register PDF font %s: %s", path, exc)

    logger.warning("No Unicode TTF found — PDF math may show missing glyphs")
    return "Helvetica"


def pdf_body_font() -> str:
    return register_pdf_unicode_font()
