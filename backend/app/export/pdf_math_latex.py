"""
Exam text → LaTeX for matplotlib mathtext → PNG in ReportLab PDFs.

Prose stays in Paragraph (spaces preserved). Only short math spans are rendered as LaTeX images.
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Literal, Union

from app.generation.question_text import ensure_plain_text

logger = logging.getLogger(__name__)

TRIG = r"sin|cos|tan|sec|cosec|cot"
MAX_SEGMENT_INPUT = 6000
MAX_MATH_SPAN = 100
MAX_DISPLAY_LATEX = 320

DOLLAR_DISPLAY = re.compile(r"\$\$([^$]+)\$\$")
DOLLAR_INLINE = re.compile(r"\$([^$\n]+)\$")
BOLD_MD = re.compile(r"\*\*([^*]+)\*\*")
_PAREN_FRAC = re.compile(r"\(([^()]+)\)\s*/\s*\(([^()]+)\)")


@dataclass(frozen=True)
class TextSegment:
    kind: Literal["text"]
    value: str


@dataclass(frozen=True)
class MathSegment:
    kind: Literal["math"]
    latex: str
    display: bool


Segment = Union[TextSegment, MathSegment]

# Bounded inline math patterns (no greedy [^,;.]+)
_INLINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"\b(?:{TRIG})\s*\^?\{{-1\}}?\s*\(\s*\d+\s*/\s*\d+\s*\)"
        rf"(?:\s*\+\s*(?:{TRIG})\s*\^?\{{-1\}}?\s*\(\s*\d+\s*/\s*\d+\s*\))*",
        re.I,
    ),
    re.compile(
        rf"\b(?:{TRIG})\s*\(\s*[A-Za-z]\s*\+\s*[A-Za-z]\s*\)\s*=\s*"
        rf"\([^)]{{1,{MAX_MATH_SPAN}}}\)\s*/\s*\([^)]{{1,{MAX_MATH_SPAN}}}\)",
        re.I,
    ),
    re.compile(
        rf"\b(?:{TRIG})\s*\(\s*\d*\s*θ\s*\)\s*=\s*"
        rf"\([^)]{{1,{MAX_MATH_SPAN}}}\)\s*/\s*\([^)]{{1,{MAX_MATH_SPAN}}}\)",
        re.I,
    ),
    re.compile(rf"\b(?:{TRIG})\s*θ\s*=\s*[\d.]+(?:\s*/\s*[\d.]+)?", re.I),
    re.compile(rf"\b(?:{TRIG})\s*θ(?:\s*cos\s*θ)?", re.I),
    re.compile(rf"\b(?:{TRIG})\s*\(\s*[^)]{{1,40}}\s*\)", re.I),
    re.compile(rf"∠\s*[A-Z]{{1,4}}\s*=\s*[^,;.\n]{{1,{MAX_MATH_SPAN}}}", re.I),
    re.compile(r"π\s*/\s*\d+", re.I),
    re.compile(r"√\s*\d+\s*/\s*\d+", re.I),
    re.compile(
        rf"\b(?:cos|sin)\s*\(\s*[A-Za-z]\s*\+\s*[A-Za-z]\s*\)\s*=\s*-?√?\s*\d+\s*/\s*\d+",
        re.I,
    ),
    re.compile(rf"\bsin\s*θ\s*cos\s*θ\s*=\s*√\s*\d+\s*/\s*\d+", re.I),
    re.compile(
        rf"(?:\b(?:{TRIG})\s+){{1,2}}[A-Z](?:\s+[A-Z])?\s*=\s*"
        rf"\([^)]{{1,{MAX_MATH_SPAN}}}\)\s*/\s*\([^)]{{1,{MAX_MATH_SPAN}}}\)",
        re.I,
    ),
    re.compile(r"√\s*\([^)]{1,40}\)", re.I),
    re.compile(r"(?:[xyz]\s*)?√\s*\(\s*1\s*-\s*[xyz](?:\^2|²)\s*\)", re.I),
    re.compile(r"\d+\s*°\s*≤\s*θ\s*≤\s*\d+\s*°?", re.I),
    re.compile(
        r"(?:\d+\s*)?x[²2]\s*[+\-−]\s*(?:\d+|[a-z]+)\s*x\s*[+\-−]\s*(?:\d+|[a-z]+)\s*=\s*0",
        re.I,
    ),
    re.compile(r"x[²2]\s*[+\-−]\s*[a-z]\s*x\s*[+\-−]\s*[a-z]\s*=\s*0", re.I),
    re.compile(
        r"p_\{n\}\s*=\s*[sstαβγ]\s*[·]?\s*p_\{n-1\}\s*[-−]\s*[sstαβγ]\s*[·]?\s*p_\{n-2\}",
        re.I,
    ),
    re.compile(r"\b\d+\s*/\s*\d+\b", re.I),
    re.compile(r"\([A-Za-zαβγ]+\s*\+\s*[A-Za-zαβγ]+\)\s*[²2]", re.I),
]


def normalize_prose_glued(text: str) -> str:
    """Restore spaces in English prose (never run on LaTeX)."""
    if not text or len(text) > 800:
        return text
    out = text
    fixes = (
        (r"([a-z])([A-Z])", r"\1 \2"),
        (r"\bIf(?=tan|sin|cos|sec|cot|find|the|angle|prove)", r"If ", re.I),
        (r"\band(?=tan|sin|cos|find|the)", r"and ", re.I),
        (r"(\d+)and(?=tan|sin|cos)", r"\1 and ", re.I),
        (r"\bfind(?=the)", r"find ", re.I),
        (r"\bthe(?=values)", r"the ", re.I),
        (r"\bvaluesof", r"values of ", re.I),
        (r"\buseit\b", r"use it ", re.I),
        (r"\bprove(?=that)", r"prove ", re.I),
        (r"\bintriangle\b", r"in triangle ", re.I),
        (r"\binterms\b", r"in terms ", re.I),
        (r"\bliesin\b", r"lies in ", re.I),
        (r"\bquadrant([IVX]+)", r"quadrant \1", re.I),
    )
    for item in fixes:
        if len(item) == 3:
            out = re.sub(item[0], item[1], out, flags=item[2])
        else:
            out = re.sub(item[0], item[1], out)
    return re.sub(r" +", " ", out)


def _replace_paren_fractions(s: str) -> str:
    out = s
    for _ in range(10):
        out, n = _PAREN_FRAC.subn(r"\\frac{\1}{\2}", out)
        if n == 0:
            break
    return out


def _normalize_plain(s: str) -> str:
    if not s:
        return ""
    out = s
    out = re.sub(r"\bsin\s*inverse\b", "sin^{-1}", out, flags=re.I)
    out = re.sub(r"\bcos\s*inverse\b", "cos^{-1}", out, flags=re.I)
    out = re.sub(r"\btan\s*inverse\b", "tan^{-1}", out, flags=re.I)
    out = re.sub(r"\b(sin|cos|tan|sec|cosec|cot)\s*⁻¹", r"\1^{-1}", out, flags=re.I)
    out = re.sub(r"\b(sin|cos|tan|sec|cosec|cot)\s*−\s*1\b", r"\1^{-1}", out, flags=re.I)
    return out.replace("−", "-").replace("–", "-").replace("×", r" \times ")


def exam_plain_to_latex(plain: str) -> str:
    """Convert a short math span to matplotlib-safe LaTeX."""
    s = _normalize_plain(plain.strip())
    if not s or len(s) > MAX_DISPLAY_LATEX:
        return s[:MAX_DISPLAY_LATEX]

    s = s.replace("θ", r"\theta")
    s = s.replace("π", r"\pi")
    s = re.sub(r"∠\s*", r"\\angle ", s)
    s = re.sub(r"√\s*\(([^)]+)\)", r"\\sqrt{\1}", s)
    s = re.sub(r"√\s*([0-9a-zA-Z]+)", r"\\sqrt{\1}", s)
    s = re.sub(r"√\s*(\d+)\s*/\s*(\d+)", r"\\frac{\\sqrt{\1}}{\2}", s)
    s = s.replace("²", "^{2}").replace("³", "^{3}")
    s = s.replace("≤", r" \leq ").replace("≥", r" \geq ").replace("≠", r" \neq ")

    s = _replace_paren_fractions(s)

    s = re.sub(
        rf"\b({TRIG})\s*\^?\{{-1\}}\s+([a-zA-Z])\b",
        lambda m: f"\\{m.group(1).lower()}^{{-1}} {m.group(2)}",
        s,
        flags=re.I,
    )
    s = re.sub(
        rf"\b({TRIG})\s*\^?\{{-1\}}\b",
        lambda m: f"\\{m.group(1).lower()}^{{-1}}",
        s,
        flags=re.I,
    )
    s = re.sub(
        rf"\b({TRIG})\s*\(\s*(\d*)\s*θ\s*\)",
        lambda m: f"\\{m.group(1).lower()}({m.group(2)}\\theta)",
        s,
        flags=re.I,
    )
    s = re.sub(
        rf"\b({TRIG})\s*\(",
        lambda m: f"\\{m.group(1).lower()}(",
        s,
        flags=re.I,
    )
    s = re.sub(
        rf"\b({TRIG})\s+([A-Z])\b",
        lambda m: f"\\{m.group(1).lower()} {m.group(2)}",
        s,
        flags=re.I,
    )
    s = re.sub(rf"\b({TRIG})\s+θ\b", lambda m: f"\\{m.group(1).lower()} \\theta", s, flags=re.I)
    s = re.sub(rf"\b({TRIG})\b", lambda m: f"\\{m.group(1).lower()}", s, flags=re.I)

    s = re.sub(r"(\d+)\s*θ", r"\1\\theta", s)
    s = re.sub(r"\bθ\b", r"\\theta", s)
    s = re.sub(r"\\pi\s*/\s*(\d+)", r"\\frac{\\pi}{\1}", s)
    s = re.sub(r"(\d+)\s*/\s*(\d+)", r"\\frac{\1}{\2}", s)
    s = re.sub(r"(\w+)\s*\*\s*(\d+)", r"\1 \\cdot \2", s)
    s = re.sub(r"([A-Z])\s*\^\s*2\b", r"\1^{2}", s)
    s = s.replace("α", r"\alpha").replace("β", r"\beta").replace("γ", r"\gamma")
    s = re.sub(r"([a-z])_\{([^{}]+)\}", r"\1_{\2}", s)
    s = re.sub(r"\\cdot\s+p_", r"\\,p_", s)
    s = re.sub(r"\\cdot\s+\\alpha", r"\\,\\alpha", s)
    s = re.sub(r"\\cdot\s+\\beta", r"\\,\\beta", s)

    return re.sub(r"\s+", " ", s).strip()


def _should_display_math(latex: str, plain: str) -> bool:
    if re.search(r"p_\{n\}", latex) and "=" in plain:
        return True
    if "\\frac" in latex and "=" in plain:
        return True
    if len(plain) > 42 and re.search(r"\\tan|\\sin|\\cos", latex):
        return True
    if plain.count("=") >= 2 and "\\frac" in latex:
        return True
    return len(latex) > 72


def _latex_renderable(latex: str) -> bool:
    if not latex or len(latex) > MAX_DISPLAY_LATEX:
        return False
    if re.search(r"^\s*\[|'\s*,\s*'", latex):
        return False
    if re.match(r"^\s*=\s*\\frac", latex):
        return False
    return True


def _sanitize_mathtext_body(latex: str) -> str:
    body = (latex or "").strip()
    while len(body) >= 2 and body.startswith("$") and body.endswith("$"):
        body = body[1:-1].strip()
    body = re.sub(r"\\{2,}(?=[a-zA-Z{])", r"\\", body)
    body = body.replace("*", r" \cdot ")
    return body


@dataclass
class _Span:
    start: int
    end: int
    text: str


def _find_math_spans(clause: str) -> list[_Span]:
    spans: list[_Span] = []
    for pat in _INLINE_PATTERNS:
        start = 0
        guard = 0
        while guard < 48:
            guard += 1
            m = pat.search(clause, start)
            if not m:
                break
            text = m.group(0)
            if text:
                spans.append(_Span(m.start(), m.end(), text))
            start = m.end() if m.end() > m.start() else m.start() + 1
    if not spans:
        return []
    spans.sort(key=lambda x: (x.start, -(x.end - x.start)))
    merged: list[_Span] = []
    for sp in spans:
        if not merged or sp.start >= merged[-1].end:
            merged.append(sp)
        elif sp.end > merged[-1].end:
            merged[-1] = sp
    return merged


def _split_mixed_clause(clause: str) -> List[Segment]:
    spans = _find_math_spans(clause)
    if not spans:
        return [TextSegment("text", normalize_prose_glued(clause))]
    out: List[Segment] = []
    last = 0
    for sp in spans:
        if sp.start > last:
            prose = clause[last : sp.start]
            out.append(TextSegment("text", normalize_prose_glued(prose)))
        latex = exam_plain_to_latex(sp.text)
        if latex and _latex_renderable(latex):
            out.append(
                MathSegment("math", latex, _should_display_math(latex, sp.text))
            )
        else:
            out.append(TextSegment("text", normalize_prose_glued(sp.text)))
        last = sp.end
    if last < len(clause):
        out.append(TextSegment("text", normalize_prose_glued(clause[last:])))
    return out


def _merge_text_segments(segments: List[Segment]) -> List[Segment]:
    merged: List[Segment] = []
    for seg in segments:
        if merged and seg.kind == "text" and merged[-1].kind == "text":
            merged[-1] = TextSegment("text", merged[-1].value + seg.value)
        else:
            merged.append(seg)
    return merged


def _parse_dollars(text: str) -> List[Segment]:
    segments: List[Segment] = []
    last = 0
    combined = re.compile(r"\$\$([^$]+)\$\$|\$([^$\n]+)\$")
    for m in combined.finditer(text):
        if m.start() > last:
            segments.append(TextSegment("text", text[last : m.start()]))
        display = m.group(0).startswith("$$")
        latex = (m.group(1) if display else m.group(2) or "").strip()
        if _latex_renderable(latex):
            segments.append(MathSegment("math", latex, display))
        else:
            segments.append(TextSegment("text", m.group(0)))
        last = m.end()
    if last < len(text):
        segments.append(TextSegment("text", text[last:]))
    return segments or [TextSegment("text", text)]


def _split_clauses(text: str) -> List[str]:
    parts: List[str] = []
    last = 0
    for m in re.finditer(
        r"(\bprove\s+that\s*:?\s*|\bHence\s*,?\s*|\bOR\s+|\.\s+(?=[A-Z(]))",
        text,
        re.I,
    ):
        if m.start() > last:
            parts.append(text[last : m.start()])
        parts.append(m.group(0))
        last = m.end()
    if last < len(text):
        parts.append(text[last:])
    return parts or [text]


def segment_exam_math(text: str) -> List[Segment]:
    if not text:
        return []
    plain = ensure_plain_text(text)
    if len(plain) > MAX_SEGMENT_INPUT:
        return [TextSegment("text", plain)]
    if "$" in plain:
        return _parse_dollars(plain)
    out: List[Segment] = []
    blocks = re.split(r"\n(?=\([ivx]+\)\s)", plain, flags=re.I)
    for block in blocks:
        for clause in _split_clauses(block):
            out.extend(_split_mixed_clause(clause))
    return _merge_text_segments(out) or [TextSegment("text", plain)]


def segment_with_bold(text: str) -> List[tuple[bool, List[Segment]]]:
    plain = ensure_plain_text(text or "")
    if len(plain) > MAX_SEGMENT_INPUT:
        return [(False, [TextSegment("text", plain)])]
    parts: List[tuple[bool, List[Segment]]] = []
    last = 0
    for m in BOLD_MD.finditer(plain):
        if m.start() > last:
            parts.append((False, segment_exam_math(plain[last : m.start()])))
        parts.append((True, [TextSegment("text", m.group(1))]))
        last = m.end()
    if last < len(plain):
        parts.append((False, segment_exam_math(plain[last:])))
    return parts or [(False, segment_exam_math(plain))]


def has_math_segments(text: str) -> bool:
    for _b, segs in segment_with_bold(text):
        if any(s.kind == "math" for s in segs):
            return True
    return False


@lru_cache(maxsize=512)
def _latex_png_cached(latex: str, fontsize: float, display: bool, dpi: int) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    body = _sanitize_mathtext_body(latex)
    wrap = f"${body}$"
    fig_w = 7.0 if display else 6.0
    fig_h = 0.75 if display else 0.38
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    fs = fontsize * (1.2 if display else 1.05)
    ax.text(
        0.5 if display else 0.02,
        0.5,
        wrap,
        fontsize=fs,
        ha="center" if display else "left",
        va="center",
        color="#1e293b",
    )
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.08,
        facecolor="white",
        edgecolor="none",
    )
    plt.close(fig)
    return buf.getvalue()


def latex_to_png_bytes(
    latex: str,
    *,
    fontsize: float = 11.0,
    display: bool = False,
    dpi: int | None = None,
) -> bytes:
    from app.core.config import settings

    if dpi is None:
        dpi = int(getattr(settings, "PDF_MATH_DPI", 150) or 150)
    return _latex_png_cached(latex, fontsize, display, dpi)
