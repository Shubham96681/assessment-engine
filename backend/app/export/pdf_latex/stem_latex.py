"""
Plain exam stems → LaTeX (display \\[\\], thin-space multiplication, sub-parts).
"""
from __future__ import annotations

import re

from app.export.pdf_math_latex import segment_exam_math

_LATEX_ESC = re.compile(r"([\\%$&#_{}~^])")
_SUBPART = re.compile(r"\s*\(([ivx]+)\)\s*", re.I)
_GREEK_UNICODE = (
    ("α", r"\alpha"),
    ("β", r"\beta"),
    ("γ", r"\gamma"),
    ("δ", r"\delta"),
    ("θ", r"\theta"),
    ("π", r"\pi"),
    ("Δ", r"\Delta"),
)


def escape_latex_prose(text: str) -> str:
    if not text:
        return ""
    out = _LATEX_ESC.sub(r"\\\1", text)
    return out.replace("\n", r"\\ ").replace("·", r"\textperiodcentered{}")


def _polish_math_latex(body: str) -> str:
    """Board-style: implied multiplication s·p_{n-1} → s\\,p_{n-1}."""
    out = body
    for uni, cmd in _GREEK_UNICODE:
        out = out.replace(uni, cmd)
    out = re.sub(r"\\cdot\s+", r"\\,", out)
    out = re.sub(r"\s+\\cdot\s+", r"\\,", out)
    out = re.sub(r"\\times\s+", r"\\,", out)
    return out


def _prefer_display(body: str, plain: str, flagged: bool) -> bool:
    if flagged:
        return True
    if len(body) > 48:
        return True
    if "\\frac" in body and "=" in plain:
        return True
    if re.search(r"p_\{n\}", body) and "=" in body:
        return True
    if plain.count("=") >= 2:
        return True
    return False


def _format_math(body: str, plain: str, display: bool) -> str:
    body = _polish_math_latex(body.strip())
    if not body:
        return ""
    if _prefer_display(body, plain, display):
        return f"\n\\[\n    {body}\n\\]\n"
    return f"${body}$"


def _render_segments(text: str) -> str:
    if not text.strip():
        return ""
    chunks: list[str] = []
    for seg in segment_exam_math(text):
        if seg.kind == "math":
            formatted = _format_math(seg.latex, seg.latex, seg.display)
            if formatted:
                chunks.append(formatted)
        else:
            val = escape_latex_prose(seg.value)
            if val.strip():
                chunks.append(val)
    return " ".join(chunks) if chunks else escape_latex_prose(text)


def stem_to_latex_body(text: str) -> str:
    """Prose + display math; (i)(ii)(iii) as labelled sub-parts."""
    if not text:
        return ""
    markers = list(_SUBPART.finditer(text))
    if not markers:
        return _render_segments(text)

    blocks: list[str] = []
    pos = 0
    intro = text[: markers[0].start()].strip()
    if intro:
        blocks.append(_render_segments(intro))

    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        label = m.group(1).lower()
        body = _render_segments(text[start:end].strip())
        blocks.append(
            f"\\noindent\\textbf{{({label})}}\\par\\vspace{{2pt}}\n{body}\\par\\vspace{{4pt}}"
        )
        pos = end

    return "\n\n".join(blocks)
