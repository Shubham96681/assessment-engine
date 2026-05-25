"""
Section dominance — foreign-topic token ratio in compiled prompts.

Lexical purity can pass while geometry priors still dominate token mass.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_TOPIC_LEXICON: Dict[str, Tuple[str, ...]] = {
    "quadratic": (
        "quadratic",
        "discriminant",
        "factoris",
        "factoriz",
        "roots",
        "polynomial",
        "x²",
        "x^2",
        "parameter k",
        "equal roots",
        "nature of roots",
        "breadth",
        "area",
        "speed",
        "consecutive",
        "sum of squares",
        "quadratic formula",
        "ax²",
        "bx",
        "word problem",
    ),
    "geometry": (
        "tangent",
        "secant",
        "chord",
        "circle",
        "radius",
        "concentric",
        "cyclic",
        "centre",
        "center",
        "point of contact",
        "aob",
        "atb",
        "pa = pb",
        "ta²",
        "tc·td",
        "tc * td",
        "quadrilateral angle sum",
        "tangent_pair",
        "dashed radii",
        "external point",
        "idiomatic geometry",
        "reasoning graph diversity",
    ),
    "quadrilaterals": (
        "parallelogram",
        "rhombus",
        "trapezium",
        "diagonal",
        "midpoint theorem",
        "opposite sides",
    ),
}

_CHAPTER_PRIMARY = {
    "quadratic": "quadratic",
    "circles": "geometry",
    "quadrilaterals": "quadrilaterals",
    "generic": "quadratic",
}

# High-signal foreign tokens per locked chapter (not shared lexicon noise like "area"/"speed")
_CHAPTER_FOREIGN_TERMS: Dict[str, Tuple[str, ...]] = {
    "quadratic": (
        "tangent",
        "secant",
        "chord",
        "concentric",
        "point of contact",
        "ta²",
        "tc·td",
        "angle aob",
        "dashed radii",
        "prove that pa = pb",
        "tangent_pair",
        "idiomatic geometry",
        "reasoning graph diversity — circles",
    ),
    "circles": (
        "discriminant",
        "quadratic equation",
        "factorisation",
        "factorization",
        "nature of roots",
        "parallelogram",
        "rhombus",
        "trapezium",
        "hard mode — quadratic",
        "reasoning diversity — quadratic",
    ),
    "quadrilaterals": (
        "tangent",
        "secant",
        "discriminant",
        "quadratic",
        "concentric",
        "ta²",
    ),
}

_CHAPTER_PRIMARY_TERMS: Dict[str, Tuple[str, ...]] = {
    "quadratic": _TOPIC_LEXICON["quadratic"],
    "circles": _TOPIC_LEXICON["geometry"],
    "quadrilaterals": _TOPIC_LEXICON["quadrilaterals"],
}


def _count_hits(text: str, terms: Tuple[str, ...]) -> int:
    low = text.lower()
    n = 0
    for term in terms:
        t = term.lower()
        if len(t) <= 3 and t.isalpha():
            if re.search(rf"\b{re.escape(t)}\b", low):
                n += 1
        elif t in low:
            n += 1
    return n


def _prompt_lines_for_dominance(prompt: str, locked_chapter: str) -> str:
    """Drop ban-list lines so FORBIDDEN declarations do not inflate foreign ratio."""
    from app.generation.prompt_purity import _is_forbidden_declaration_line
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    pack = get_chapter_rule_pack(locked_chapter)
    banned = tuple(pack.forbidden_terms)
    kept: List[str] = []
    for line in prompt.splitlines():
        if _is_forbidden_declaration_line(line, banned_terms=banned):
            continue
        kept.append(line)
    return "\n".join(kept)


def compute_topic_distribution(prompt: str, *, locked_chapter: str = "") -> Dict[str, float]:
    """
    Normalized hit counts per topic family (not true NLP — fast compile guard).
    """
    if not prompt:
        return {"quadratic": 0.0, "geometry": 0.0, "quadrilaterals": 0.0}
    body = (
        _prompt_lines_for_dominance(prompt, locked_chapter)
        if locked_chapter
        else prompt
    )
    counts = {
        "quadratic": _count_hits(body, _TOPIC_LEXICON["quadratic"]),
        "geometry": _count_hits(body, _TOPIC_LEXICON["geometry"]),
        "quadrilaterals": _count_hits(body, _TOPIC_LEXICON["quadrilaterals"]),
    }
    total = sum(counts.values()) or 1
    return {k: round(v / total, 4) for k, v in counts.items()}


def foreign_topic_ratio(prompt: str, locked_chapter: str) -> float:
    """
    Ratio of foreign high-signal hits vs primary+foreign hits.
    Uses chapter-specific foreign terms (avoids 'area'/'speed' false positives on Circles).
    """
    ch = (locked_chapter or "generic").strip().lower()
    body = _prompt_lines_for_dominance(prompt, ch) if ch else prompt
    foreign_terms = _CHAPTER_FOREIGN_TERMS.get(ch, ())
    primary_terms = _CHAPTER_PRIMARY_TERMS.get(ch, _TOPIC_LEXICON["quadratic"])
    if not foreign_terms:
        dist = compute_topic_distribution(prompt, locked_chapter=ch)
        if ch == "generic":
            # Do not assume quadratic is primary — use dominant lexicon bucket
            dominant = max(dist, key=lambda k: dist[k])
            return round(1.0 - dist.get(dominant, 0.0), 4)
        primary_key = _CHAPTER_PRIMARY.get(ch, "quadratic")
        return round(1.0 - dist.get(primary_key, 0.0), 4)

    foreign_hits = _count_hits(body, foreign_terms)
    primary_hits = _count_hits(body, primary_terms)
    total = foreign_hits + primary_hits
    if total == 0:
        return 0.0
    return round(foreign_hits / total, 4)


def validate_section_dominance(
    prompt: str,
    locked_chapter: str,
    *,
    max_foreign_ratio: float = 0.08,
    min_primary_ratio: float = 0.28,
) -> Dict[str, Any]:
    ch = (locked_chapter or "generic").strip().lower()
    dist = compute_topic_distribution(prompt, locked_chapter=ch)
    primary_key = _CHAPTER_PRIMARY.get(ch, "quadratic")
    primary = dist.get(primary_key, 0.0)
    if ch in _CHAPTER_FOREIGN_TERMS:
        body = _prompt_lines_for_dominance(prompt, ch)
        ph = _count_hits(body, _CHAPTER_PRIMARY_TERMS.get(ch, ()))
        fh = _count_hits(body, _CHAPTER_FOREIGN_TERMS.get(ch, ()))
        total = ph + fh
        primary = round(ph / total, 4) if total else primary
    foreign = foreign_topic_ratio(prompt, ch)
    flags: List[str] = []
    if foreign > max_foreign_ratio:
        flags.append(f"foreign_topic_ratio:{foreign:.3f}>{max_foreign_ratio}")
    if primary < min_primary_ratio and ch != "generic":
        flags.append(f"weak_primary_topic:{primary_key}:{primary:.3f}")
    return {
        "topic_distribution": dist,
        "foreign_topic_ratio": foreign,
        "primary_topic_ratio": primary,
        "section_dominance_ok": not flags,
        "section_dominance_flags": flags,
    }


def should_reject_section_dominance(
    prompt: str,
    locked_chapter: str,
    *,
    max_foreign_ratio: float = 0.08,
) -> bool:
    report = validate_section_dominance(
        prompt, locked_chapter, max_foreign_ratio=max_foreign_ratio
    )
    return not report.get("section_dominance_ok", True)
