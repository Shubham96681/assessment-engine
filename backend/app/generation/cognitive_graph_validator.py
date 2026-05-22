"""
Cognitive graph validation — difficulty from theorem dependency, not step count.

Rejects:
- textbook theorem recall masquerading as L5
- OR bifurcation instead of HOTS fusion
- shallow concentric on L3+ hard slots
- stems that expose the solution path (no hiddenness)
- inference depth below slot band (theorem families, not Step 1..5 labels)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.reasoning_signature import (
    extract_reasoning_signature,
    reasoning_signature_for_question,
    signature_key,
)

# Distinct theorem families detected in stem+answer (not step labels)
_FAMILY_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("perpendicular_radius", r"\bperpendicular\b|radius\s*⟂|⟂\s*(?:tangent|chord|ab|rs)"),
    ("equal_tangents", r"\bequal\s+tangents?\b|congruen|rhs\b|cpct\b"),
    ("quadrilateral_sum", r"\bquadrilateral\b|180\s*°|supplementary\b"),
    ("central_angle", r"\bcentral\s+angle\b|angle\s+[A-Z]O[A-Z]\b"),
    ("cyclic_angle", r"\bcyclic\b|major\s+arc|circumference\b|angle\s+[A-Z]{3}.*\b(?:arc|major)"),
    ("power_of_point", r"\b(?:\^|²|2)\s*=.*[·x×]|power\s+of\s+point|ta\s*[·x×]\s*td"),
    ("similarity", r"\bsimilar\b|\baa\b|\bsas\b.*\bsimilar"),
    ("concentric_bisect", r"\bconcentric\b|bisect|half[\s-]?chord|inner\s+circle.*\btouch"),
    ("pythagoras_length", r"\bpythagoras\b|√|\bsqrt\b|\^\s*2\s*=\s*\d"),
    ("secant_identify", r"\bsecant\b"),
    ("auxiliary_construction", r"\bjoin\b|\bconstruct\b|\bauxiliary\b"),
    ("converse_trap", r"\bconverse\b|if\s+.*\s+then\s+.*\s+prove"),
)

_POWER_PROVE = re.compile(
    r"\bprove\s+that\s+[A-Z]{2}\s*(?:\^|²|2)?\s*=\s*[A-Z]{2}\s*(?:[·x×\.]\s*)?[A-Z]{2}\b",
    re.I,
)
_OR_SPLIT = re.compile(r"\bor\b|\*\*or\*\*", re.I)


def _text(q: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ("content", "correct_answer", "answer", "explanation"):
        v = q.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def count_theorem_families(text: str) -> List[str]:
    low = (text or "").lower()
    found: List[str] = []
    for fam, pat in _FAMILY_PATTERNS:
        if re.search(pat, low, re.I) or re.search(pat, text or "", re.I):
            found.append(fam)
    seen: set[str] = set()
    out: List[str] = []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def canonical_graph_id(q: Dict[str, Any]) -> str:
    """Isomorphism key: same proof skeleton regardless of point labels."""
    stem = q.get("content") or ""
    sig = reasoning_signature_for_question(q)
    families = ":".join(sorted(count_theorem_families(_text(q))[:5]))
    # Collapse tangent-pair angle chase variants
    if sig.startswith("tangent_pair:") and (
        "angle_find" in sig or "central_angle" in sig or "cyclic" in families
    ):
        if re.search(r"\bmajor\s+arc\b", stem, re.I) or re.search(
            r"\bfind\s+angle\s+[A-Z]{3}\b.*\bfind\s+angle\s+[A-Z]{3}\b",
            stem,
            re.I,
        ):
            return "GRAPH:tangent_pair_cyclic_angle_chase"
    if sig.startswith("concentric:") or (
        "concentric" in sig and "chord_touching_inner" in sig
    ):
        if re.search(r"\bfind\b", stem, re.I) and not re.search(r"\(i\)|\(ii\)", stem):
            return "GRAPH:concentric_chord_length_direct"
    if "secant_tangent" in (q.get("archetype_id") or "") and _POWER_PROVE.search(stem):
        return "GRAPH:textbook_power_of_point"
    if sig in (
        "prove_equal_tangents:pythagoras",
        "prove_equal_tangents:pythagoras:length_compute",
    ):
        return "GRAPH:equal_tangents_then_radius"
    return f"GRAPH:{sig}|{families}"


def stem_hiddenness_score(stem: str, archetype: str) -> float:
    """
    1.0 = delayed recognition; 0.0 = theorem path obvious in stem.
    """
    if not stem:
        return 0.5
    low = stem.lower()
    score = 1.0
    if _POWER_PROVE.search(stem) and re.search(r"\btangent\b", low) and re.search(
        r"\bsecant\b", low
    ):
        score -= 0.55
    if re.search(r"\bprove\s+that\s+[A-Z]{2}\s*=\s*[A-Z]{2}\b", stem, re.I) and re.search(
        r"\btangents?\b", low
    ):
        score -= 0.35
    if re.search(r"\bfind\s+[A-Z]{2}\b", stem, re.I) and re.search(
        r"\bO[A-Z]\s*=\s*\d", stem, re.I
    ) and re.search(r"\bradius\b|\btangent\b", low):
        if not re.search(r"\bhence\b|\busing\b.*\b(?:arc|cyclic|secant)\b", low):
            score -= 0.25
    if archetype == "hots_mixed" and _OR_SPLIT.search(stem):
        parts = _OR_SPLIT.split(stem)
        if len(parts) >= 2:
            score -= 0.2
    return max(0.0, min(1.0, score))


def is_textbook_theorem_recall(
    stem: str,
    answer: str,
    *,
    archetype: str,
    band: str,
) -> bool:
    """L5 prove EY² = EB·EC with no disguised structure."""
    if band not in ("L4", "L5"):
        return False
    if archetype not in ("secant_tangent", "tangent_similarity", "direct_theorem"):
        return False
    if not _POWER_PROVE.search(stem):
        return False
    combined = f"{stem} {answer}".lower()
    twist_markers = (
        "cyclic",
        "similar",
        "auxiliary",
        "quadrilateral",
        "hence find",
        "alternate segment",
        "midpoint",
        "contradiction",
    )
    return not any(m in combined for m in twist_markers)


def is_hots_bifurcation(stem: str, *, band: str, archetype: str) -> bool:
    """OR splits independent easy branches — opposite of fusion."""
    if band != "L5" or archetype != "hots_mixed":
        return False
    if not _OR_SPLIT.search(stem):
        return False
    low = stem.lower()
    has_i_ii = bool(re.search(r"\(i\)|\(ii\)", low))
    angle_branch = bool(
        re.search(r"\bfind\s+angle\b", low)
        or (
            has_i_ii
            and re.search(r"angle\s+[A-Z]{3}\s*=", stem, re.I)
            and "find" in low
        )
    )
    len_branch = bool(
        re.search(r"\bprove\b.*\bfind\b", low)
        or (
            re.search(r"\bO[A-Z]\s*=\s*\d", stem, re.I)
            and re.search(r"\bfind\s+[A-Z]{2}\b", stem, re.I)
        )
    )
    if angle_branch and len_branch and not re.search(
        r"\bhence\b.*\b(?:find|prove)\b|\busing\s+(?:the\s+)?(?:above|result)\b",
        low,
    ):
        return True
    parts = _OR_SPLIT.split(stem)
    if len(parts) >= 2 and angle_branch and len_branch:
        return True
    return False


def is_shallow_concentric_hard(stem: str, answer: str, *, band: str) -> bool:
    """Concentric chord find with only ⟂ + bisect + Pythagoras (2 families)."""
    if "concentric" not in stem.lower():
        return False
    if re.search(r"\(i\)|\(ii\)|prove.*bisect", stem, re.I):
        return False
    fams = count_theorem_families(f"{stem} {answer}")
    shallow_set = {"perpendicular_radius", "concentric_bisect", "pythagoras_length"}
    if set(fams).issubset(shallow_set) and len(fams) <= 3:
        if band in ("L3", "L4", "L5"):
            return True
    return False


def inference_depth_ok(
    families: List[str],
    *,
    band: str,
    stem: str,
) -> bool:
    """Minimum distinct theorem families by cognitive band."""
    n = len(families)
    min_f = {"L1": 1, "L2": 2, "L3": 2, "L4": 3, "L5": 3}.get(band, 2)
    if band in ("L4", "L5") and n < min_f:
        return False
    if band == "L3" and n < 2 and re.search(r"\bfind\b", stem, re.I):
        return False
    return n >= min_f


def prior_graphs_from_stems(stems: List[str]) -> List[str]:
    """Build canonical graph ids from prior stem previews (for prompt exclusion)."""
    graphs: List[str] = []
    for stem in stems:
        if not stem:
            continue
        q = {"content": stem, "archetype_id": ""}
        gid = canonical_graph_id(q)
        if gid not in graphs:
            graphs.append(gid)
    return graphs[:20]


def evaluate_cognitive_graph(
    q: Dict[str, Any],
    *,
    slot_meta: Optional[Dict[str, Any]] = None,
    ui_difficulty: str = "medium",
) -> Dict[str, Any]:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return {
            "cognitive_graph_ok": True,
            "cognitive_graph_score": 1.0,
            "cognitive_graph_flags": [],
            "canonical_graph_id": canonical_graph_id(q),
        }

    stem = q.get("content") or ""
    answer = _text(q)
    meta = slot_meta or {}
    band = meta.get("band") or q.get("slot_band") or "L3"
    archetype = (
        meta.get("archetype_id") or q.get("archetype_id") or ""
    ).strip()
    flags: List[str] = []
    score = 1.0

    gid = canonical_graph_id(q)
    q["canonical_graph_id"] = gid

    families = count_theorem_families(answer)
    q["theorem_families"] = families
    q["theorem_family_count"] = len(families)

    hidden = stem_hiddenness_score(stem, archetype)
    q["stem_hiddenness"] = round(hidden, 3)
    if band in ("L4", "L5") and hidden < 0.45:
        flags.append("theorem_path_exposed_in_stem")
        score -= 0.35

    if not inference_depth_ok(families, band=band, stem=stem):
        flags.append(f"low_theorem_family_depth:{len(families)}_for_{band}")
        score -= 0.4

    if is_textbook_theorem_recall(stem, answer, archetype=archetype, band=band):
        flags.append("textbook_theorem_recall")
        score -= 0.5

    if is_hots_bifurcation(stem, band=band, archetype=archetype):
        flags.append("hots_or_bifurcation_not_fusion")
        score -= 0.55

    if is_shallow_concentric_hard(stem, answer, band=band):
        flags.append("shallow_concentric_chain")
        score -= 0.35
        if band == "L3" and meta.get("archetype_id") == "length_find":
            flags.append("length_find_not_hard_without_fusion")
            score -= 0.2

    sig = q.get("reasoning_signature") or reasoning_signature_for_question(q)
    if band in ("L4", "L5") and gid == "GRAPH:tangent_pair_cyclic_angle_chase":
        if sig.startswith("tangent_pair:") and q.get("reasoning_duplicate"):
            flags.append("repeat_tangent_pair_cyclic_chase")
            score -= 0.4

    cog_score = max(0.0, min(1.0, score))
    critical = (
        "textbook_theorem_recall",
        "hots_or_bifurcation_not_fusion",
        "theorem_path_exposed_in_stem",
    )
    if any(f.startswith("low_theorem_family_depth") for f in flags):
        critical = critical + ("low_theorem_family_depth",)
    if "shallow_concentric_chain" in flags and band in ("L3", "L4", "L5"):
        critical = critical + ("shallow_concentric_chain",)
    ok = cog_score >= 0.52 and not any(
        f == c or f.startswith(c) for f in flags for c in critical
    )
    return {
        "cognitive_graph_ok": ok,
        "cognitive_graph_score": round(cog_score, 3),
        "cognitive_graph_flags": flags,
        "canonical_graph_id": gid,
    }


def should_reject_cognitive_graph(
    q: Dict[str, Any],
    *,
    slot_meta: Optional[Dict[str, Any]] = None,
    ui_difficulty: str = "medium",
) -> bool:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return False
    if "cognitive_graph_ok" not in q:
        q.update(
            evaluate_cognitive_graph(
                q, slot_meta=slot_meta, ui_difficulty=ui_difficulty
            )
        )
    return not q.get("cognitive_graph_ok", True)


def cognitive_graph_prompt_block(chapter: str = "circles") -> str:
    ch = (chapter or "generic").lower()
    if ch != "circles":
        return ""
    return """
COGNITIVE GRAPH (hard mode — validated after generation):
- Difficulty = distinct theorem FAMILIES chained (not Step 1..5 count).
- L3 hard: ≥2 families; L4: ≥3; L5: ≥4 OR disguised reuse with hidden first step.
- BAN L5: bare "Prove TR² = TA·TC" with only tangent+secant named (textbook recall).
- BAN L5 HOTS: OR between angle-find branch AND tangent-length branch (bifurcation).
- GOOD L5: one configuration → hidden lemma → Hence second result (same figure).
- BAN: concentric chord find with only ⟂ + bisect + Pythagoras on L3+ hard slot.
- Stems must NOT announce the theorem (no naked power-of-point prove without twist).
- NEVER repeat reasoning graph: tangent_pair + major arc + two angle finds = one signature.
""".strip()
