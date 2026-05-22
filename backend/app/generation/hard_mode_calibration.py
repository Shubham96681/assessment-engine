"""
Hard-mode reasoning-depth control — enforces L4/L5 paper when UI difficulty is hard.

Authenticity/compression are not enough; hard mode requires theorem chains,
hidden inference, and banned one-step templates (direct Pythagoras-only, naming drills).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.solution_difficulty import score_solution_difficulty

# Stem pattern tags
TAG_DIRECT_PYTHAGORAS = "direct_pythagoras_only"
TAG_CONCEPTUAL_RECALL = "conceptual_recall"
TAG_NAME_ONLY = "name_only"
TAG_STANDARD_PROOF = "standard_proof"
TAG_ANGLE_CHAIN = "angle_chain"
TAG_HOTS_MIXED = "hots_mixed"
TAG_CONCENTRIC = "concentric_multi"
TAG_HIDDEN_TRAP = "hidden_trap"
TAG_TRIVIAL_ANGLE_SUM = "trivial_angle_sum"
TAG_TRIVIAL_CONCENTRIC = "trivial_concentric_find"
TAG_DISCONNECTED_OR = "disconnected_or_branches"
TAG_DIAGRAM_ONLY_PROOF = "diagram_only_proof"

_BAND_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}

# Minimum solution band by blueprint slot band (hard UI only)
SLOT_MIN_SOLUTION_BAND: Dict[str, str] = {
    "L1": "L2",
    "L2": "L2",
    "L3": "L3",
    "L4": "L4",
    "L5": "L4",
}

# Slots that forbid weak stem classes when UI = hard
SLOT_FORBIDDEN_STEM_TAGS: Dict[str, Tuple[str, ...]] = {
    "L3": (TAG_DIRECT_PYTHAGORAS, TAG_NAME_ONLY, TAG_TRIVIAL_ANGLE_SUM, TAG_TRIVIAL_CONCENTRIC),
    "L4": (
        TAG_DIRECT_PYTHAGORAS,
        TAG_NAME_ONLY,
        TAG_CONCEPTUAL_RECALL,
        TAG_TRIVIAL_ANGLE_SUM,
        TAG_TRIVIAL_CONCENTRIC,
        TAG_DISCONNECTED_OR,
        TAG_DIAGRAM_ONLY_PROOF,
    ),
    "L5": (
        TAG_DIRECT_PYTHAGORAS,
        TAG_NAME_ONLY,
        TAG_CONCEPTUAL_RECALL,
        TAG_STANDARD_PROOF,
        TAG_TRIVIAL_ANGLE_SUM,
        TAG_TRIVIAL_CONCENTRIC,
        TAG_DISCONNECTED_OR,
        TAG_DIAGRAM_ONLY_PROOF,
    ),
}

# Geometry-only rules live in chapter_prompt_isolation.CIRCLES_HARD_RULES
from app.generation.chapter_prompt_isolation import (
    CIRCLES_HARD_RULES as HARD_PAPER_RULES,
    hard_mode_prompt_block,
)


def classify_stem(stem: str) -> List[str]:
    """Heuristic stem archetype tags for calibration."""
    if not stem:
        return []
    low = stem.lower().strip()
    tags: List[str] = []

    if re.match(r"^can\s+.+\?$", low) or re.match(r"^is\s+.+\?$", low):
        tags.append(TAG_CONCEPTUAL_RECALL)
    if re.search(r"\bname\s+(?:the\s+)?(?:secant|tangent)\b", low):
        tags.append(TAG_NAME_ONLY)
    if re.search(r"\bfind\s+pq\b", low) and re.search(r"\bop\s*=\s*\d", low, re.I) and re.search(
        r"\boq\s*=\s*\d", low, re.I
    ):
        tags.append(TAG_DIRECT_PYTHAGORAS)
    if re.search(
        r"\bfind\s+(?:AP|TA|TP|TQ|PQ|KJ|EY|UW|FC|LA|GR|HX|KJ|BC|WX)\b",
        stem,
        re.I,
    ) and re.search(r"\bO[A-Z]\s*=\s*\d", stem, re.I):
        if re.search(r"\bradius\b|O[A-Z]\s*=\s*\d", stem, re.I):
            if not re.search(r"\(i\)|\(ii\)|prove.*bisect|concentric", low):
                tags.append(TAG_DIRECT_PYTHAGORAS)
    if re.search(
        r"\bprove\s+that\s+[A-Z]{2}\s*(?:\^|²|2|\s*\.\s*[A-Z]{2})\s*=\s*[A-Z]{2}",
        stem,
        re.I,
    ) or re.search(r"\bprove\s+that\s+[A-Z]{2}²\s*=\s*[A-Z]{2}", stem, re.I):
        if not (re.search(r"\btangent\b", low) and re.search(r"\bsecant\b", low)):
            tags.append(TAG_DIAGRAM_ONLY_PROOF)
    if "**or**" in low or re.search(r"\bor\b", low):
        has_angle = bool(
            re.search(r"\bfind\s+angle\b", low)
            or (
                re.search(r"\bfind\s+[A-Z]{3}\b", stem, re.I)
                and re.search(r"angle\s+[A-Z]{3}\s*=", stem, re.I)
            )
        )
        has_len = bool(
            re.search(r"\bfind\s+[A-Z]{2}\b", stem, re.I)
            and re.search(r"\bO[A-Z]\s*=\s*\d", stem, re.I)
        )
        if has_angle and has_len:
            tags.append(TAG_DISCONNECTED_OR)
    if re.search(r"\bprove\s+that\s+pa\s*=\s*pb\b", low):
        if not re.search(r"\bhence\b|\bif\s+angle\b|\bor\s+prove", low):
            tags.append(TAG_STANDARD_PROOF)
    if re.search(r"\bfind\s+angle\b", low) and re.search(
        r"angle\s+[A-Z]{3}\b.*angle\s+[A-Z]{3}\b|if\s+angle", stem, re.I
    ):
        tags.append(TAG_ANGLE_CHAIN)
        if re.search(r"angle\s+\w+\s*=\s*\d+°?", stem, re.I) and not re.search(
            r"\bor\b|\(i\)|\(ii\)|prove", low
        ):
            tags.append(TAG_TRIVIAL_ANGLE_SUM)
    if " or " in low and (re.search(r"\bprove\b", low) or re.search(r"\bhence\b", low)):
        tags.append(TAG_HOTS_MIXED)
    if re.search(r"\bconcentric\b|\bchord\b.*\btouch", low):
        tags.append(TAG_CONCENTRIC)
        if re.search(r"\bfind\b", low) and not re.search(r"\(i\)|\(ii\)|prove", low):
            tags.append(TAG_TRIVIAL_CONCENTRIC)
    if re.search(r"\bfind\s+ap\b|\bfind\s+ta\b", low, re.I) and re.search(
        r"\boa?\s*=\s*\d|\bop\s*=\s*\d", low, re.I
    ) and TAG_DIRECT_PYTHAGORAS not in tags:
        tags.append(TAG_HIDDEN_TRAP)
    return tags


def _band_at_least(actual: str, minimum: str) -> bool:
    return _BAND_ORDER.get(actual, 0) >= _BAND_ORDER.get(minimum, 99)


def _classify_quadratic_stem(stem: str) -> List[str]:
    low = (stem or "").lower()
    tags: List[str] = []
    if re.search(r"\bdiscriminant\b|nature\s+of\s+roots", low):
        tags.append("discriminant_nature")
    if re.search(r"\bequal\s+roots\b|coincident\s+roots|\bfind\s+k\b", low):
        tags.append("equal_roots_k")
    if re.search(r"\bfactoris", low):
        tags.append("factorisation")
    if re.search(r"\barea\b|\bbreadth\b|\blength\b.*\bwidth\b|grove|plot|path", low):
        tags.append("area_word")
    if re.search(r"\bspeed\b|\bkm/h\b|\bhour\b.*\blonger\b", low):
        tags.append("speed_time")
    if " or " in low and re.search(r"\bfind\b|\bform\b", low):
        tags.append(TAG_HOTS_MIXED)
    return tags


def evaluate_hard_mode(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
    slot_meta: Optional[Dict[str, Any]] = None,
    locked_chapter: str = "",
) -> Dict[str, Any]:
    """
    Returns hard_mode_ok, hard_mode_score, hard_mode_flags for a question.
    """
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return {"hard_mode_ok": True, "hard_mode_score": 1.0, "hard_mode_flags": []}

    stem = (q.get("content") or "").strip()
    meta = slot_meta or {}
    chapter = (locked_chapter or q.get("locked_chapter") or "").lower()
    if chapter == "quadratic":
        stem_tags = _classify_quadratic_stem(stem)
        # Reject circle leakage in quadratic chapter
        if re.search(
            r"\b(circle|tangent|secant|radius|chord|concentric|angle\s+aob)\b",
            stem,
            re.I,
        ):
            flags_pre = ["geometry_leak_in_quadratic"]
            return {
                "hard_mode_ok": False,
                "hard_mode_score": 0.2,
                "hard_mode_flags": flags_pre,
                "stem_tags": stem_tags,
            }
    else:
        stem_tags = classify_stem(stem)
    sol = score_solution_difficulty(q)
    q.update(sol)

    flags: List[str] = []
    score = 1.0
    band = slot_band or meta.get("band", "L3")
    min_sol = SLOT_MIN_SOLUTION_BAND.get(band, "L3")
    sol_band = q.get("solution_band", "L1")

    if not _band_at_least(sol_band, min_sol):
        flags.append(f"solution_too_shallow:{sol_band}_needs_{min_sol}")
        score -= 0.45

    forbidden = SLOT_FORBIDDEN_STEM_TAGS.get(band, ())
    if meta.get("sparse_hard") and TAG_STANDARD_PROOF in stem_tags:
        forbidden = tuple(t for t in forbidden if t != TAG_STANDARD_PROOF)
    for tag in stem_tags:
        if tag in forbidden:
            flags.append(f"forbidden_stem_{tag}_for_{band}")
            score -= 0.35

    sig = q.get("reasoning_signature") or ""
    if sig in (
        "tangent_pair:quadrilateral:central_angle",
        "tangent_pair:quadrilateral:angle_between",
    ):
        if band in ("L4", "L5"):
            flags.append("shallow_tangent_pair_angle_for_band")
            score -= 0.35
        elif band == "L3" and q.get("reasoning_duplicate"):
            flags.append("duplicate_tangent_pair_reasoning")
            score -= 0.3

    if q.get("reasoning_duplicate"):
        flags.append("reasoning_graph_duplicate_in_paper")
        score -= 0.4

    if band in ("L4", "L5"):
        if q.get("theorem_count", 0) < 2:
            flags.append("insufficient_theorem_markers")
            score -= 0.2
        if q.get("fusion_count", 0) < 1 and q.get("dependency_depth", 0) < 3:
            flags.append("insufficient_theorem_fusion")
            score -= 0.25
        ans_low = ""
        for key in ("correct_answer", "answer"):
            v = q.get(key)
            if isinstance(v, str):
                ans_low += v.lower()
        proof_rich = "congruent" in ans_low or "rhs" in ans_low or "hence" in ans_low
        if q.get("hidden_steps", 0) < 2 and "prove" in stem.lower() and not proof_rich:
            flags.append("proof_too_shallow")
            score -= 0.25
        if q.get("dependency_depth", 0) < 2:
            flags.append("low_inference_depth")
            score -= 0.2

    if band == "L5" and TAG_ANGLE_CHAIN not in stem_tags and TAG_HOTS_MIXED not in stem_tags:
        if TAG_CONCEPTUAL_RECALL in stem_tags or TAG_NAME_ONLY in stem_tags:
            flags.append("l5_not_hots")
            score -= 0.4
        elif q.get("solution_difficulty", 0) < 0.55:
            flags.append("l5_low_solution_graph")
            score -= 0.3

    if meta.get("one_line_ok") and TAG_CONCEPTUAL_RECALL in stem_tags:
        pass  # allowed only when slot marks one_line_ok
    elif TAG_CONCEPTUAL_RECALL in stem_tags and band in ("L3", "L4", "L5"):
        if not meta.get("one_line_ok"):
            flags.append("conceptual_in_hard_slot")
            score -= 0.3

    hard_score = max(0.0, min(1.0, score))
    has_forbidden = any(f.startswith("forbidden_stem_") for f in flags)
    has_shallow = any("solution_too_shallow" in f for f in flags)
    return {
        "hard_mode_ok": hard_score >= 0.58 and not has_forbidden and not has_shallow,
        "hard_mode_score": round(hard_score, 3),
        "hard_mode_flags": flags,
        "stem_tags": stem_tags,
    }


def should_reject_hard_mode(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
    slot_meta: Optional[Dict[str, Any]] = None,
    locked_chapter: str = "",
) -> bool:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return False
    report = evaluate_hard_mode(
        q,
        slot_band=slot_band,
        ui_difficulty=ui,
        slot_meta=slot_meta,
        locked_chapter=locked_chapter,
    )
    q.update(report)
    if not report.get("hard_mode_ok", True):
        return True
    flags = report.get("hard_mode_flags") or []
    critical = (
        "solution_too_shallow",
        "forbidden_stem_direct_pythagoras",
        "forbidden_stem_disconnected_or",
        "forbidden_stem_diagram_only_proof",
        "forbidden_stem_name_only",
        "l5_not_hots",
        "reasoning_graph_duplicate",
        "shallow_tangent_pair_angle",
        "duplicate_tangent_pair",
    )
    if locked_chapter == "quadratic" and any("geometry_leak" in f for f in flags):
        return True
    return any(any(c in f for c in critical) for f in flags)
