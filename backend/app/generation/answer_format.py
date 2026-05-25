"""
Normalize model answers: Python list/dict blobs, duplicate (i)(i) labels, surd fractions.
"""
from __future__ import annotations

import ast
import re
from typing import List, Optional

_ROMAN = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")

# Leading sub-part labels: (i), (ii), (j), (iii), etc.
_SUBPART_PREFIX = re.compile(
    r"^\s*\(\s*(?:i{1,3}|iv|v|vi{0,3}|ix|x|[a-z])\s*\)\s*",
    re.I,
)

_QUOTED_STRINGS = re.compile(r"'((?:\\'|[^'])*)'")
_DICT_ENTRY = re.compile(
    r"['\"]?(prove|hence|part\s*\d+|answer|solution)['\"]?\s*:\s*"
    r"['\"](.+?)['\"](?=\s*[,})\]]|\s*$)",
    re.I | re.S,
)
_GIBBERISH = re.compile(r"cos\||A---|\\2/|mathsf\s*\{", re.I)
_EMPTY_PART = re.compile(r"^\s*\(\s*[a-z]\s*\)\s*,?\s*$", re.I)
_TRAIL_COMMA = re.compile(r"([0-9°θπ√)\]]+)\s*,\s*(?=\n|$)")
_MATHSF_COMMA = re.compile(r"</math>\s*,", re.I)
# √(ii) or 3/3(ii) — sub-part label glued to previous math
_GLUED_SUBPART = re.compile(
    r"(?<=[0-9°√²³π\)\w/])\s*\(\s*(i{1,3}|iv|v|vi{0,3}|vii|viii|ix|x)\s*\)",
    re.I,
)
_SUBPART_LINE = re.compile(
    r"^\s*\(\s*(i{1,3}|iv|v|vi{0,3}|vii|viii|ix|x)\s*\)\s*(.*)$",
    re.I,
)


def _roman_label(index: int) -> str:
    if 0 <= index < len(_ROMAN):
        return f"({_ROMAN[index]})"
    return f"({index + 1})"


def unglue_subparts(text: str) -> str:
    """Insert newlines before (ii)(iii) crushed onto end of prior part (e.g. √10/3(ii))."""
    if not text:
        return text
    out = _GLUED_SUBPART.sub(lambda m: f"\n({m.group(1).lower()}) ", text)
    return re.sub(r"\n{3,}", "\n\n", out)


def strip_subpart_prefixes(text: str) -> str:
    """Remove stacked (i) (ii) / (j) (ii) prefixes."""
    out = (text or "").strip()
    for _ in range(6):
        m = _SUBPART_PREFIX.match(out)
        if not m:
            break
        out = out[m.end() :].strip()
    return out


def _strip_line_commas(line: str) -> str:
    line = _MATHSF_COMMA.sub("", line)
    line = _TRAIL_COMMA.sub(r"\1", line)
    return line.rstrip(" ,").strip()


def _is_gibberish(item: str) -> bool:
    if not item or len(item.strip()) < 4:
        return True
    if _GIBBERISH.search(item):
        return True
    if _EMPTY_PART.match(item):
        return True
    # Mostly punctuation / broken LaTeX
    alnum = sum(1 for c in item if c.isalnum())
    return alnum < max(6, len(item) // 8)


def _parse_quoted_list(text: str) -> Optional[List[str]]:
    t = text.strip()
    if not t.startswith("[") or "'" not in t:
        return None
    items = [m.group(1).replace("\\'", "'") for m in _QUOTED_STRINGS.finditer(t)]
    return items if len(items) >= 1 else None


def _parse_dict_blob(text: str) -> Optional[List[str]]:
    t = text.strip()
    if not re.search(r"['\"]?\w+['\"]?\s*:", t):
        return None
    items = [m.group(2).strip() for m in _DICT_ENTRY.finditer(t)]
    if items:
        return items
    # Try ast after paren-dict → brace-dict coercion
    if t.startswith("(") and ":" in t:
        coerced = "{" + t[1:]
        if coerced.endswith(")"):
            coerced = coerced[:-1] + "}"
        coerced = coerced.replace("'", '"')
        try:
            data = ast.literal_eval(coerced)
            if isinstance(data, dict):
                return [str(v) for v in data.values() if v]
        except (SyntaxError, ValueError):
            pass
    return None


def _try_literal_list(text: str) -> Optional[List[str]]:
    t = text.strip()
    if not (t.startswith("[") or t.startswith("(")):
        return None
    try:
        data = ast.literal_eval(t)
    except (SyntaxError, ValueError):
        return None
    if isinstance(data, (list, tuple)):
        return [str(x) for x in data]
    if isinstance(data, dict):
        return [str(v) for v in data.values()]
    return None


def _split_subpart_lines(text: str) -> List[str]:
    """Split on newlines or inline (i) markers."""
    t = unglue_subparts(text.strip())
    if not t:
        return []
    if "\n" in t:
        return [ln.strip() for ln in t.splitlines() if ln.strip()]
    parts = re.split(r"(?=\(\s*(?:i{1,3}|iv|v|vi{0,3})\s*\))", t, flags=re.I)
    return [p.strip() for p in parts if p.strip()]


def split_answer_subparts(text: str) -> List[tuple[str, str]]:
    """
    Return [(label, body), ...] when answer has 2+ sub-parts; else [].
    """
    formatted = unglue_subparts(format_structured_answer(text or ""))
    if not formatted:
        return []
    rows: List[tuple[str, str]] = []
    for line in formatted.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _SUBPART_LINE.match(line)
        if m:
            label = f"({m.group(1).lower()})"
            body = (m.group(2) or "").strip()
            rows.append((label, body))
        elif rows:
            prev_l, prev_b = rows[-1]
            rows[-1] = (prev_l, f"{prev_b} {line}".strip())
        else:
            rows.append(("", line))
    labeled = [(l, b) for l, b in rows if b]
    if len(labeled) < 2:
        return []
    return labeled


def format_structured_answer(text: str) -> str:
    """
    Turn Python list/dict answers into (i)(ii)(iii) plain text with sane labels.
    Idempotent on already-formatted answers.
    """
    if not text:
        return text
    raw = text.strip()
    if len(raw) > 12000:
        return raw

    items: Optional[List[str]] = None
    items = _parse_quoted_list(raw) or _parse_dict_blob(raw) or _try_literal_list(raw)

    if items is None and raw.startswith("["):
        items = _parse_quoted_list(raw)

    if items is not None:
        cleaned: List[str] = []
        for item in items:
            body = strip_subpart_prefixes(_strip_line_commas(str(item)))
            if _is_gibberish(body):
                continue
            cleaned.append(body)
        if not cleaned:
            return "[Answer incomplete — regenerate this question]"
        lines = [_roman_label(i) + " " + body for i, body in enumerate(cleaned)]
        return "\n".join(lines)

    # Multi-line / inline (i)(ii) without list wrapper — re-label consistently
    if re.search(r"\(\s*i{1,3}\s*\)", raw, re.I) or "\n" in raw:
        chunks = _split_subpart_lines(raw)
        if len(chunks) >= 2:
            cleaned = []
            for ch in chunks:
                body = strip_subpart_prefixes(_strip_line_commas(ch))
                if _is_gibberish(body):
                    continue
                if body:
                    cleaned.append(body)
            if cleaned:
                return "\n".join(
                    _roman_label(i) + " " + body for i, body in enumerate(cleaned)
                )

    # Single blob fixes
    out = unglue_subparts(_strip_line_commas(strip_subpart_prefixes(raw)))
    out = re.sub(r"\bs\s+solve\b", "Solve", out, flags=re.I)
    out = re.sub(r"\(\s*[m-z]\s*\)\s*,\s*", "", out, flags=re.I)
    return out


def looks_structured_answer(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith("[") and "'" in t:
        return True
    if re.match(r"^\(\s*['\"]?\w+['\"]?\s*:", t):
        return True
    if _GIBBERISH.search(t):
        return True
    return bool(re.search(r"\(\s*i{1,3}\s*\).*\(\s*i{1,3}\s*\)", t, re.I))


def ensure_answer_text(text: str) -> str:
    """Format list/dict answers then plain-text sanitize."""
    from app.generation.question_text import ensure_plain_text

    if not text:
        return text
    return ensure_plain_text(format_structured_answer(text))
