"""
Quadratic coefficient / word-problem registry — block exact reuse across generations.

Tracks factor triples (a,b,c), area (length, breadth, area), and speed (distance, Δv, Δt).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

_EQ_RE = re.compile(
    r"(?:(\d+)\s*)?x²\s*([+\−-])\s*(\d+)\s*x\s*([+\−-])\s*(\d+)",
    re.I,
)
_AREA_RE = re.compile(
    r"length\s*\(([^)]+)\).*?breadth\s*\(([^)]+)\).*?area\s*(?:is\s*)?(\d+)\s*m",
    re.I | re.S,
)
_SPEED_RE = re.compile(
    r"(\d+)\s*km\s+at\s+[a-z]\s*km/h",
    re.I,
)
_SPEED_RETURN_RE = re.compile(r"\(\s*[a-z]\s*\+\s*(\d+)\s*\)\s*km/h", re.I)
_TIME_DIFF_RE = re.compile(
    r"(\d+|½|1/2|1/3|2/3|3/4)\s*(?:hour|h)\s+less",
    re.I,
)


def _norm_expr(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").lower().replace("−", "-"))


def _sign(ch: str) -> int:
    return -1 if ch in ("−", "-", "–") else 1


def signature_factorisation(stem: str) -> Optional[str]:
    m = _EQ_RE.search((stem or "").replace(" ", ""))
    if not m:
        return None
    a = int(m.group(1) or "1")
    b = _sign(m.group(2)) * int(m.group(3))
    c = _sign(m.group(4)) * int(m.group(5))
    return f"fac:{a},{b},{c}"


def signature_area(stem: str) -> Optional[str]:
    m = _AREA_RE.search(stem or "")
    if not m:
        return None
    return f"area:{_norm_expr(m.group(1))}|{_norm_expr(m.group(2))}|{m.group(3)}"


def signature_speed(stem: str) -> Optional[str]:
    low = stem or ""
    dm = _SPEED_RE.search(low)
    rm = _SPEED_RETURN_RE.search(low)
    tm = _TIME_DIFF_RE.search(low)
    if not dm or not rm or not tm:
        return None
    return f"speed:{dm.group(1)}|+{rm.group(1)}|{tm.group(1)}"


def signatures_from_stem(stem: str) -> List[str]:
    out: List[str] = []
    for fn in (signature_factorisation, signature_area, signature_speed):
        sig = fn(stem)
        if sig:
            out.append(sig)
    return out


def collect_signatures(stems: List[str]) -> Set[str]:
    found: Set[str] = set()
    for s in stems:
        for sig in signatures_from_stem(s):
            found.add(sig)
    return found


def build_banned_registry_block(prior_stems: List[str], *, max_lines: int = 20) -> str:
    """Compact block for rag_query.txt even in COMPACT PROMPT MODE."""
    if not prior_stems:
        return ""
    sigs: List[str] = []
    for stem in prior_stems:
        sigs.extend(signatures_from_stem(stem))
    if not sigs:
        return ""
    unique = list(dict.fromkeys(sigs))[:max_lines]
    lines = [
        "BANNED COEFFICIENT REGISTRY — do NOT reuse these exact sets (invent new numbers):",
    ]
    for sig in unique:
        if sig.startswith("fac:"):
            parts = sig[4:].split(",")
            lines.append(f"- Factorisation triple (a,b,c) = ({parts[0]}, {parts[1]}, {parts[2]})")
        elif sig.startswith("area:"):
            body = sig[5:]
            length, breadth, area = body.split("|")
            lines.append(
                f"- Area model: length ({length}), breadth ({breadth}), area {area} m²"
            )
        elif sig.startswith("speed:"):
            body = sig[6:].split("|")
            lines.append(
                f"- Speed/time: {body[0]} km, return offset {body[1]} km/h, time diff {body[2]} h"
            )
    lines.append("")
    return "\n".join(lines)


def filter_questions_matching_prior_registry(
    questions: List[Dict[str, Any]],
    prior_stems: List[str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Drop pool items whose signature exactly matches a prior stem."""
    banned = collect_signatures(prior_stems)
    if not banned:
        return questions, []
    kept: List[Dict[str, Any]] = []
    rejected: List[str] = []
    for q in questions:
        stem = (q.get("content") or q.get("question") or "").strip()
        sigs = set(signatures_from_stem(stem))
        overlap = sigs & banned
        if overlap:
            rejected.append(f"{(stem or '')[:60]} [{next(iter(overlap))}]")
            continue
        kept.append(q)
    return kept, rejected


_ARCHETYPE_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"factoris", "factorisation_roots"),
    (r"nature\s+of\s+(?:the\s+)?roots|state\s+the\s+nature|for\s+all\s+real", "nature_of_roots"),
    (r"equal\s+(?:real\s+)?roots|d\s*=\s*0", "equal_roots_parameter"),
    (r"rectangle|area\s+\d+\s*m", "word_problem_area"),
    (r"quadratic\s+formula", "formula_roots"),
    (r"answer\s+one\s+of\s+the\s+following", "formula_roots"),
    (r"km/h|km\s+at\s+[a-z]", "hots_quad"),
)


def detect_archetypes_in_paper(questions: Sequence[Dict[str, Any]]) -> Set[str]:
    found: Set[str] = set()
    for q in questions:
        stem = (q.get("content") or q.get("question") or "").lower()
        for pat, tag in _ARCHETYPE_PATTERNS:
            if re.search(pat, stem, re.I):
                found.add(tag)
    return found


def evaluate_archetype_coverage(
    questions: Sequence[Dict[str, Any]],
    *,
    require_or: bool = False,
) -> Tuple[bool, List[str]]:
    """
  For full-hard quadratic papers, expect core archetypes in the delivered set.
  """
    found = detect_archetypes_in_paper(questions)
    required = {
        "factorisation_roots",
        "nature_of_roots",
        "equal_roots_parameter",
        "word_problem_area",
    }
    optional_one_of = {"formula_roots", "hots_quad"}
    flags: List[str] = []
    missing = required - found
    if missing:
        flags.append(f"missing_archetypes:{','.join(sorted(missing))}")
    if not (found & optional_one_of):
        flags.append("missing_hots_or_formula")
    if require_or and "formula_roots" not in found:
        flags.append("missing_or_branch")
    return (not flags, flags)
