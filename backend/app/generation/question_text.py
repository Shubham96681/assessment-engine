"""
Normalize question stems for UI and PDF — prompts use **OR** markdown but viewers are plain/HTML only.
"""
from __future__ import annotations

import re
from typing import Callable
from xml.sax.saxutils import escape

_BOLD_MD = re.compile(r"\*\*([^*]+)\*\*")
_LATEX_CMD = re.compile(
    r"\\(?:sqrt|frac|sin|cos|tan|log|ln)\b\*?(?:\{[^{}]*\})*"
    r"|\\[a-zA-Z]+\b\*?(?:\{[^{}]*\})*"
    r"|\$\$?[^$]+\$\$?",
    re.I,
)
_LATEX_FONT_CMDS = (
    r"mathsf|mathbf|mathrm|mathit|text|textit|textbf|sf|rm|mit|mathcal"
)
_LATEX_FONT_WRAPPER = re.compile(
    rf"\\(?:{_LATEX_FONT_CMDS})\s*\{{\s*([^{{}}]*?)\s*\}}",
    re.I,
)
_LATEX_EMPTY_FONT = re.compile(
    rf"\\(?:{_LATEX_FONT_CMDS})\s*\{{\s*\}}",
    re.I,
)
_LATEX_BARE_FONT = re.compile(
    rf"\\(?:{_LATEX_FONT_CMDS})\b\*?\s*",
    re.I,
)
_LATEX_SPACING = re.compile(r"\\[,;!\s]+")
_LATEX_SUM = re.compile(r"\\sum\b\*?", re.I)
_LATEX_WEDGE = re.compile(r"\\\^?\{\\wedge\}|\^\{\\wedge\}", re.I)
_LATEX_TIMES = re.compile(r"\\times\b|\\cdot\b", re.I)
_LATEX_LINE_BREAK = re.compile(r"\\\\+")
_ANY_LATEX_CMD = re.compile(r"\\[a-zA-Z]+\*?(?:\{[^{}]*\})*")
_RAW_LATEX_RE = re.compile(
    rf"\\(?:{_LATEX_FONT_CMDS}|sum|wedge|times|cdot)\b|\\[a-zA-Z]{{2,}}|\\\\",
    re.I,
)
_POINT_LABEL_PAIR = re.compile(
    r"\b([A-Z])\s+([A-Z])(?=\s*[=^²]|\s*cm\b|\s*[×x]\s*[A-Z]|\)|,|\.)",
)
_LATEX_DOLLAR = re.compile(r"\$+([^$]+)\$+")
_LABEL_SPACE_EQ = re.compile(r"\b([A-Z])\s+([A-Z])\s*=")
_BRACE_SUP = re.compile(r"\^\{([^{}]*)\}")
_BRACE_SUB = re.compile(r"_\{([^{}]*)\}")

_HTML_TAG = re.compile(r"<[^>]+>", re.I)
_HTML_HR = re.compile(r"<\s*hr\s*/?\s*>", re.I)
_HR_PARTIAL = re.compile(
    r"(?<![a-zA-Z])(?:<\s*)?,?\s*hr\s*/?\s*>?(?=\s|\.|,|;|:|$|\bHence\b|\bOR\b)",
    re.I,
)
_HR_ARTIFACT = re.compile(
    r"(?<=[°\w\)\.])\s*,?\s*hr\s*/\s*(?=\s*(?:Hence|OR|[A-Z(])|\.)",
    re.I,
)
_GEO_SYMBOLS: tuple[tuple[str, str], ...] = (
    ("\u27c2", " is perpendicular to "),
    ("\u22a5", " is perpendicular to "),
    ("\u2225", " is parallel to "),
    ("\u2013", "-"),
    ("\u2014", "-"),
    ("\u2212", "-"),
    ("\u00d7", " x "),
)
_MATHSF_REMNANT = re.compile(r"\bmathsf\b", re.I)
_MODELS_REMNANT = re.compile(r"\bmodels\w*\b", re.I)
_GH_MATHSF_GLUE = re.compile(r"([A-Z])mathsf\s+mathsf\s+([A-Z])", re.I)
_G_MATHSF_H = re.compile(r"([A-Z])mathsf\s+([A-Z])", re.I)
_INNER_RADIUS_OF_CORRUPT = re.compile(
    r"\binner radius\s+O\s+(?:models\w*\s+)?(?:sq\s+)?Z?\s*(\d+(?:\.\d+)?)?\s*cm",
    re.I,
)
_SECANT_PT_GARBAGE = re.compile(
    r"\s*(?:and\s+)?(?:the\s+)?(?:fu(?:ll)?\s+)?secant\s+P\s+to\s+T\s+is\s+PT\s*=\s*\d+(?:\.\d+)?\s*cm\.?",
    re.I,
)
# Geometry labels that must stay glued (PR not P R / misread as PB in PDF)
_CIRCLE_LABELS = (
    "PA", "PB", "PQ", "PR", "PT", "OA", "OP", "OF", "OD", "OE", "DE", "DF",
    "GH", "GJ", "GK", "OG", "OA", "BC", "AB", "CD", "EF",
)
_DIGIT_LETTER_GLUE = re.compile(r"(\d)([A-Za-z])")
_EQ_NO_SPACE = re.compile(r"=\s*(\d)")
_CM_NO_SPACE = re.compile(r"(\d)\s*cm\b", re.I)
_IF_GH_NO_EQ = re.compile(r"\bIf\s+GH\s+(\d+(?:\.\d+)?)\s*cm\b", re.I)
_GH_NO_EQ = re.compile(r"\bGH\s+(?!=)(\d+(?:\.\d+)?)\s*cm\b", re.I)
_TRUNC_FRO = re.compile(r"\bfro\s+(?!m\b)", re.I)
_CMANT_GLUE = re.compile(r"\bcmant\b", re.I)
_MARK_GLUE = re.compile(r"(\d)\.0mar\b", re.I)


def _collapse_latex_backslashes(text: str) -> str:
    """JSON/LLM often double-escapes: \\\\mathsf → \\mathsf → \\mathsf."""
    out = text
    for _ in range(8):
        prev = out
        out = re.sub(r"\\{2,}(?=[a-zA-Z{])", r"\\", out)
        if out == prev:
            break
    return out


def normalize_stem_for_pdf(text: str) -> str:
    """Fix glued tokens, missing '=', spacing around measurements."""
    if not text:
        return text
    out = text
    out = re.sub(r"\bQuestion\s+(\d)([a-zA-Z])", r"Question \1 \2", out, flags=re.I)
    # "Question 2touching" → "Question 2 touching" (full word after digit)
    out = re.sub(
        r"\bQuestion\s+(\d+)([a-zA-Z]{2,})",
        r"Question \1 \2",
        out,
        flags=re.I,
    )
    out = _TRUNC_FRO.sub("from ", out)
    out = _CMANT_GLUE.sub("cm and", out)
    out = _MARK_GLUE.sub(r"\1.0 mark", out)
    out = _IF_GH_NO_EQ.sub(r"If GH = \1 cm", out)
    out = _GH_NO_EQ.sub(r"GH = \1 cm", out)
    out = _DIGIT_LETTER_GLUE.sub(r"\1 \2", out)
    out = _EQ_NO_SPACE.sub(r"= \1", out)
    out = _CM_NO_SPACE.sub(r"\1 cm", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip()


def _collapse_geometry_labels(text: str) -> str:
    """P R → PR, G H → GH (after LaTeX \\mathsf{P R} strips)."""
    out = text
    for label in _CIRCLE_LABELS:
        if len(label) == 2:
            out = re.sub(
                rf"\b{label[0]}\s+{label[1]}\b",
                label,
                out,
                flags=re.I,
            )
    return out


def fix_secant_answer_variables(stem: str, answer: str) -> str:
    """Q2 asks for PR — never leave PB from garbled \\mathsf{P B}."""
    if not stem or not answer:
        return answer
    if re.search(r"\bFind\s+PR\b|\bPR\b.*\bsecant\b", stem, re.I):
        return re.sub(r"\bPB\b", "PR", answer)
    return answer


def _finalize_display_math(text: str) -> str:
    """Board-style Unicode: GH² = GJ × GK (not G H^2 or raw LaTeX)."""
    if not text:
        return text
    out = _collapse_geometry_labels(text)
    for _ in range(5):
        prev = out
        out = _POINT_LABEL_PAIR.sub(r"\1\2", out)
        if out == prev:
            break
    out = re.sub(r"\b([A-Z]{2,})\^2\b", r"\1²", out)
    out = re.sub(r"\b([A-Z])\s+([A-Z])\^2\b", r"\1\2²", out)
    out = re.sub(r"\b(\d+)\^2\b", r"\1²", out)
    out = normalize_paper_superscripts(out)
    # PA2= / GH2= / DF2= → PA²= (after LaTeX strip drops caret)
    out = re.sub(
        r"\b([A-Z]{2})2(?=\s*[=×+\-]|\s*=\s*|\s*×\s*|\s*-\s*)",
        r"\1²",
        out,
    )
    out = re.sub(r"\b([A-Z]{2})2=", r"\1²=", out)
    out = re.sub(
        r"\bsquare root of\s+(\d+(?:\.\d+)?)(\s*cm\b)?",
        lambda m: f"√{m.group(1)}{m.group(2) or ''}",
        out,
        flags=re.I,
    )
    out = _MATHSF_REMNANT.sub(" ", out)
    out = _MODELS_REMNANT.sub(" ", out)
    out = _GH_MATHSF_GLUE.sub(r"\1\2", out)
    out = _G_MATHSF_H.sub(r"\1\2", out)
    out = _INNER_RADIUS_OF_CORRUPT.sub(
        lambda m: f"inner radius OF = {m.group(1) or '21'} cm",
        out,
    )
    out = _SECANT_PT_GARBAGE.sub("", out)
    out = re.sub(r"\(\s*([A-Z])\s+([A-Z])\s*\)", r"\1\2", out)
    out = re.sub(r"\(\s*([A-Z]{2,})\s*\)", r"\1", out)
    out = re.sub(r"\s+x\s+([A-Z]{1,3})\b", r" × \1", out)
    out = re.sub(
        r"(\b(?:verify|show|check)\b[^.;]{0,80})\s+x\s+",
        r"\1 × ",
        out,
        flags=re.I,
    )
    out = re.sub(r"\\[a-zA-Z]+\*?", "", out)
    out = re.sub(r"\\+", "", out)
    return re.sub(r"\s+", " ", out).strip()


def _aggressive_latex_strip(text: str) -> str:
    out = text
    for _ in range(8):
        prev = out
        out = _ANY_LATEX_CMD.sub(" ", out)
        out = re.sub(r"\\(?![nrt])", " ", out)
        if out == prev:
            break
    return out


def sanitize_latex_for_reportlab(text: str) -> str:
    """
    ReportLab Paragraph treats { } as markup — LaTeX corrupts PDF output.
    Convert to plain text (never leave \\mathsf etc. visible).
    """
    if not text:
        return text
    out = _collapse_latex_backslashes(text)
    out = re.sub(
        r"\\angle\s*\{?\s*([A-Za-zθΘ]{1,4})\s*\}?",
        lambda m: f"\u2220{m.group(1)}",
        out,
        flags=re.I,
    )
    out = out.replace("sin⁻¹", "sin inverse").replace("sin−1", "sin inverse")
    out = out.replace("cos⁻¹", "cos inverse").replace("tan⁻¹", "tan inverse")
    out = _LATEX_EMPTY_FONT.sub("", out)
    for _ in range(6):
        prev = out
        out = _LATEX_FONT_WRAPPER.sub(r"\1", out)
        if out == prev:
            break
    out = _LATEX_DOLLAR.sub(r"\1", out)
    out = _LATEX_WEDGE.sub("^", out)
    out = _LATEX_TIMES.sub(" x ", out)
    out = _LATEX_LINE_BREAK.sub(" ", out)
    out = _LATEX_BARE_FONT.sub("", out)
    out = _LATEX_SUM.sub(" ", out)
    out = _LATEX_SPACING.sub(" ", out)
    out = _LATEX_CMD.sub(" ", out)
    out = _LABEL_SPACE_EQ.sub(r"\1\2=", out)
    out = _BRACE_SUP.sub(r"^\1", out)
    out = _BRACE_SUB.sub(r"_\1", out)
    out = out.replace("{", "(").replace("}", ")")
    if _RAW_LATEX_RE.search(out):
        out = _aggressive_latex_strip(out)
        out = out.replace("{", "(").replace("}", ")")
    out = normalize_stem_for_pdf(out)
    out = _finalize_display_math(out)
    return out


def strip_html_markup(text: str) -> str:
    """LLM sometimes emits <hr/>, <br/> — must not appear in stems or PDF."""
    if not text:
        return text
    out = _HTML_HR.sub(" ", text)
    out = _HTML_TAG.sub(" ", out)
    out = _HR_PARTIAL.sub(" ", out)
    out = _HR_ARTIFACT.sub(" ", out)
    out = re.sub(r"\s+,hr\s*/", " ", out, flags=re.I)
    out = re.sub(r"(?<![a-zA-Z])hr\s*/\s*>", " ", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()


def normalize_geometry_symbols(text: str) -> str:
    """Keep ∠ and Δ symbols; normalize perpendicular/parallel tokens only."""
    if not text:
        return text
    out = text
    for src, dst in _GEO_SYMBOLS:
        out = out.replace(src, dst)
    return out


def has_raw_latex(text: str) -> bool:
    if not text:
        return False
    return bool(_RAW_LATEX_RE.search(text))


def normalize_exam_stem_spacing(text: str) -> str:
    """Fix glued OR branches, degree marks, and identity tokens before PDF/UI."""
    if not text:
        return text
    out = text
    out = out.replace("≠", "≠").replace("=!=", "≠")
    out = re.sub(r"(\d)\s*°\s*(exactly|hence)", r"\1° \2", out, flags=re.I)
    out = re.sub(r"(exactly)\s*\.\s*OR\b", r"\1. OR", out, flags=re.I)
    out = re.sub(r"([°\)])\s*exactly\s*\.\s*OR", r"\1 exactly. OR", out, flags=re.I)
    out = re.sub(r"([°\w])exactly\.?\s*OR", r"\1 exactly. OR", out, flags=re.I)
    out = re.sub(r"\.OR\b", ". OR", out)
    out = re.sub(r"\s+OR\s+", " OR ", out)
    out = re.sub(r"\bOR\s*\(", " OR (", out)
    out = re.sub(
        r"\bwhen\s+1\s*[-−]\s*tan\s*x\s*tan\s*y\s*=\s*(\d+)",
        r"when 1 − tan x tan y ≠ 0",
        out,
        flags=re.I,
    )
    out = re.sub(r"tan2θ", "tan²θ", out)
    out = re.sub(r"sin2θ", "sin²θ", out)
    out = re.sub(r"cos2θ", "cos²θ", out)
    out = re.sub(r"sec2θ", "sec²θ", out)
    out = re.sub(r"cosec2θ", "cosec²θ", out)
    out = re.sub(r"cot2θ", "cot²θ", out)
    out = re.sub(r"\s+\(i\)", " (i)", out)
    out = re.sub(r"\s+\(ii\)", " (ii)", out)
    out = re.sub(r"\s+\(iii\)", " (iii)", out)
    return out


def ensure_plain_text(text: str) -> str:
    """Idempotent: strip LaTeX/markdown until PDF-safe plain text."""
    if not text:
        return text
    out = strip_html_markup(text)
    out = normalize_exam_stem_spacing(out)
    out = normalize_geometry_symbols(
        _BOLD_MD.sub(r"\1", sanitize_latex_for_reportlab(out))
    )
    if has_raw_latex(out):
        out = normalize_geometry_symbols(
            _BOLD_MD.sub(
                r"\1",
                _finalize_display_math(
                    normalize_stem_for_pdf(
                        _aggressive_latex_strip(_collapse_latex_backslashes(text))
                    )
                ),
            )
        )
    else:
        out = _finalize_display_math(out)
    from app.generation.sympy_math_text import apply_sympy_math_symbols

    out = apply_sympy_math_symbols(out)
    out = normalize_unicode_subscripts_for_storage(out)
    return normalize_paper_math_notation(out)


def normalize_unicode_subscripts_for_storage(text: str) -> str:
    """Unicode subscripts only → p_{n-1} (superscripts stay as ², ³, ^{n} added at render)."""
    if not text:
        return text
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in _SUBSCRIPT_CHARS:
            j = i + 1
            while j < n and text[j] in _SUBSCRIPT_CHARS:
                j += 1
            sub = _unicode_subscript_to_ascii(text[i:j])
            out.append(f"_{{{sub}}}")
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def normalize_unicode_math_indices_to_plain(text: str) -> str:
    """Legacy alias — subscripts to _{…}; keeps Unicode superscripts like x²."""
    return normalize_unicode_subscripts_for_storage(text)


def strip_markdown_bold(text: str) -> str:
    """Plain text for DB + PDF prep."""
    return ensure_plain_text(text)


# Phrases that must not break across PDF lines (Paper 12: "fro GH" from line wrap)
def _nbsp_from_question(m: re.Match[str]) -> str:
    return f"from\u00a0Question\u00a0{m.group(1)}"


_PROTECTED_PHRASES: tuple[
    tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]], ...
] = (
    (re.compile(r"\bfrom\s+O;\s*tangent\b", re.I), "from\u00a0O;\u00a0tangent"),
    (re.compile(r"\bfrom\s+O\b", re.I), "from\u00a0O"),
    (re.compile(r"\btangent\s+GH\b", re.I), "tangent\u00a0GH"),
    (re.compile(r"\bfrom\s+Question\s+(\d+)\b", re.I), _nbsp_from_question),
    (re.compile(r"\bfro\s+GH\b", re.I), "from\u00a0GH"),
    (
        re.compile(r"\bfro\s+([A-Z]{2})\b", re.I),
        lambda m: f"from\u00a0{m.group(1)}",
    ),
)


def _protect_measurements_for_markup(text: str) -> str:
    def _nbsp_seg(m: re.Match) -> str:
        a, eq, num = m.group(1), m.group(2), m.group(3)
        return f"{a}\u00a0{eq}\u00a0{num}\u00a0cm"

    out = re.sub(
        r"\b([A-Z]{1,3})\s*(=)\s*(\d+(?:\.\d+)?)\s*cm\b",
        _nbsp_seg,
        text,
        flags=re.I,
    )
    out = re.sub(
        r"\b([A-Z]{1,3})\s*(=)\s*(\d+(?:\.\d+)?)(?!\s*cm)\b",
        lambda m: f"{m.group(1)}\u00a0{m.group(2)}\u00a0{m.group(3)}",
        out,
        flags=re.I,
    )
    # Keep "15 cm" on one line (Paper 11: 15 / cm split across lines)
    out = re.sub(
        r"(\d+(?:\.\d+)?)\s+cm\b",
        lambda m: f"{m.group(1)}\u00a0cm",
        out,
        flags=re.I,
    )
    for pat, repl in _PROTECTED_PHRASES:
        out = pat.sub(repl, out)
    for label in _CIRCLE_LABELS:
        if len(label) == 2:
            out = re.sub(
                rf"\b{label[0]}\s+{label[1]}\b",
                f"{label[0]}\u00a0{label[1]}",
                out,
                flags=re.I,
            )
    return re.sub(
        r"\bQuestion\s+(\d+)\b",
        lambda m: f"Question\u00a0{m.group(1)}",
        out,
        flags=re.I,
    )


_SUBSCRIPT_UNICODE: dict[str, str] = {
    "\u2080": "0",
    "\u2081": "1",
    "\u2082": "2",
    "\u2083": "3",
    "\u2084": "4",
    "\u2085": "5",
    "\u2086": "6",
    "\u2087": "7",
    "\u2088": "8",
    "\u2089": "9",
    "\u208a": "+",
    "\u208b": "-",
    "\u208c": "=",
    "\u208d": "(",
    "\u208e": ")",
    "\u2090": "a",
    "\u2091": "e",
    "\u2092": "o",
    "\u2093": "x",
    "\u2095": "h",
    "\u2096": "k",
    "\u2097": "l",
    "\u2098": "m",
    "\u2099": "n",
    "\u209a": "o",
    "\u209b": "p",
    "\u209c": "t",
}

_SUPERSCRIPT_UNICODE: dict[str, str] = {
    "\u00b2": "2",
    "\u00b3": "3",
    "\u00b9": "1",
    "\u2070": "0",
    "\u2071": "i",
    "\u2074": "4",
    "\u2075": "5",
    "\u2076": "6",
    "\u2077": "7",
    "\u2078": "8",
    "\u2079": "9",
    "\u207a": "+",
    "\u207b": "-",
    "\u207f": "n",
}

_SUBSCRIPT_CHARS = frozenset(_SUBSCRIPT_UNICODE)
_SUPERSCRIPT_CHARS = frozenset(_SUPERSCRIPT_UNICODE)

_ASCII_EXP_TO_UNICODE = str.maketrans(
    {
        "0": "\u2070",
        "1": "\u00b9",
        "2": "\u00b2",
        "3": "\u00b3",
        "4": "\u2074",
        "5": "\u2075",
        "6": "\u2076",
        "7": "\u2077",
        "8": "\u2078",
        "9": "\u2079",
        "n": "\u207f",
        "+": "\u207a",
        "-": "\u207b",
    }
)

_CARET_BRACE_EXP = re.compile(
    r"([A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9\)\]])\^\{([^{}]+)\}"
)
_CARET_ASCII_EXP = re.compile(
    r"([A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9\)\]])\^([0-9n+\-]+)"
)


def _exp_to_unicode_superscript(exp: str) -> str | None:
    if not exp or not re.fullmatch(r"[0-9n+\-]+", exp):
        return None
    return exp.translate(_ASCII_EXP_TO_UNICODE)


_SEQ_ASCII_SUB = re.compile(r"\b([a-z])_(?!\{)([a-z0-9+\-]+)\b")
_P_SEQ_NO_UNDERSCORE = re.compile(
    r"(?<![A-Za-z])p\s*(?:_)?\s*(n(?:\s*-\s*\d+)?|\d+)\b",
    re.I,
)


def normalize_paper_sequence_subscripts(text: str) -> str:
    """Board stems use p_n, p_n-1 → p_{n}, p_{n-1} for subscript rendering."""
    if not text or "_" not in text:
        return text
    return _SEQ_ASCII_SUB.sub(r"\1_{\2}", text)


def normalize_missing_p_indices(text: str) -> str:
    """
    OCR/LLM sometimes drops '_' entirely: 'p n', 'p0', 'pn-1'.
    Convert only p-indices to p_{...} so ReportLab <sub> renders.
    """
    if not text:
        return text
    if "p" not in text and "P" not in text:
        return text

    def _repl(m: re.Match[str]) -> str:
        idx = (m.group(1) or "").strip()
        idx = re.sub(r"\s*-\s*", "-", idx)
        return f"p_{{{idx}}}"

    return _P_SEQ_NO_UNDERSCORE.sub(_repl, text)


def normalize_spurious_x_multiplication(text: str) -> str:
    """Fix s x p_{n-1} (legacy ×→' x ') → s·p_{n-1}."""
    if not text or " x " not in text:
        return text
    out = re.sub(
        r"\b([a-zαβγts])\s+x\s+(p_\{)",
        r"\1·\2",
        text,
        flags=re.I,
    )
    out = re.sub(
        r"\b([a-zαβγts])\s+x\s+(p_[a-z0-9])",
        r"\1·\2",
        out,
        flags=re.I,
    )
    return out


def normalize_paper_math_notation(text: str) -> str:
    """Single entry: sequence subscripts + Unicode superscripts (PDF/UI)."""
    if not text:
        return text
    out = normalize_missing_p_indices(text)
    out = normalize_paper_sequence_subscripts(out)
    out = normalize_paper_superscripts(out)
    return normalize_spurious_x_multiplication(out)


def normalize_paper_superscripts(text: str) -> str:
    """Board-style exponents: x^2 → x², α^{n} → αⁿ (keeps p_{n} for sub rendering)."""
    if not text or "^" not in text:
        return text

    def _br(m: re.Match[str]) -> str:
        uni = _exp_to_unicode_superscript(m.group(2))
        return f"{m.group(1)}{uni}" if uni else m.group(0)

    def _plain(m: re.Match[str]) -> str:
        uni = _exp_to_unicode_superscript(m.group(2))
        return f"{m.group(1)}{uni}" if uni else m.group(0)

    out = _CARET_BRACE_EXP.sub(_br, text)
    return _CARET_ASCII_EXP.sub(_plain, out)


def _unicode_subscript_to_ascii(run: str) -> str:
    return "".join(_SUBSCRIPT_UNICODE.get(c, c) for c in run)


def _unicode_superscript_to_ascii(run: str) -> str:
    return "".join(_SUPERSCRIPT_UNICODE.get(c, c) for c in run)


_ASCII_SUP_BRACE = re.compile(r"\^\{([^{}]+)\}")
_ASCII_SUP_SINGLE = re.compile(r"\^([0-9+\-]+)")
_ASCII_SUB_BRACE = re.compile(r"_\{([^{}]+)\}")
_ASCII_SUB_SINGLE = re.compile(
    r"(?<=[A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9\)\]])_([0-9A-Za-z+\-]+)"
)
def _ascii_indices_to_reportlab_markup(text: str) -> str:
    """Render p_{n} as <sub>; keep board Unicode superscripts (x²) as literal glyphs."""
    if not text:
        return text

    text = normalize_paper_math_notation(text)

    def _uni_sub(m: re.Match[str]) -> str:
        return f"<sub>{escape(_unicode_subscript_to_ascii(m.group(0)))}</sub>"

    def _sup_tag(inner: str) -> str:
        return f"<sup>{escape(inner)}</sup>"

    def _sub_tag(inner: str) -> str:
        return f"<sub>{escape(inner)}</sub>"

    def _sup_brace(m: re.Match[str]) -> str:
        return _sup_tag(m.group(1))

    def _sup_single(m: re.Match[str]) -> str:
        return _sup_tag(m.group(1))

    def _sub_brace(m: re.Match[str]) -> str:
        return _sub_tag(m.group(1))

    def _sub_single(m: re.Match[str]) -> str:
        return _sub_tag(m.group(1))

    out = text
    out = re.sub(r"[\u2080-\u208e\u2090-\u209c]+", _uni_sub, out)
    out = _ASCII_SUP_BRACE.sub(_sup_brace, out)
    out = _ASCII_SUB_BRACE.sub(_sub_brace, out)
    out = _ASCII_SUP_SINGLE.sub(_sup_single, out)
    out = _ASCII_SUB_SINGLE.sub(_sub_single, out)
    # Force adjacency: p<n>, x<sup> (avoid any accidental spaces before tags).
    out = re.sub(
        r"([A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9\)\]])\s+(<sub\b)",
        r"\1\2",
        out,
    )
    out = re.sub(
        r"([A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9\)\]])\s+(<sup\b)",
        r"\1\2",
        out,
    )
    return _escape_outside_math_tags(out)


_MATH_TAG_SPLIT = re.compile(r"(<su[bp][^>]*>.*?</su[bp]>)")


def _escape_outside_math_tags(s: str) -> str:
    parts = _MATH_TAG_SPLIT.split(s)
    return "".join(
        p if re.match(r"<su[bp]", p) else escape(p) for p in parts
    )


def _escape_with_superscripts(text: str) -> str:
    """Map x², p_{n}, x^2 to ReportLab <sup>/<sub>; escape remaining prose."""
    if not text:
        return text
    return _ascii_indices_to_reportlab_markup(text)


def to_reportlab_markup(text: str) -> str:
    """ReportLab Paragraph markup: **OR** → <b>OR</b>, XML-escaped elsewhere."""
    if not text:
        return text

    text = ensure_plain_text(text)
    text = _protect_measurements_for_markup(text)

    parts: list[str] = []
    last = 0
    for m in _BOLD_MD.finditer(text):
        parts.append(_escape_with_superscripts(text[last : m.start()]))
        parts.append(f"<b>{escape(m.group(1))}</b>")
        last = m.end()
    parts.append(_escape_with_superscripts(text[last:]))
    return "".join(parts)
