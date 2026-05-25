"""
Reasoning-graph signatures — detect duplicate cognitive patterns across a paper.

Two stems with different labels can share the same graph, e.g.:
  tangent_pair → quadrilateral → angle_sum → central_angle
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

def _skill_family_for_archetype(archetype_id: str) -> str:
    from app.generation.rd_archetypes import ARCHETYPE_BY_ID

    arch = ARCHETYPE_BY_ID.get(archetype_id, {})
    fam = (arch.get("skill_family") or "").strip()
    if fam:
        return fam
    return ARCHETYPE_REASONING_FAMILY_LEGACY.get(archetype_id, archetype_id)


# Legacy fallback when archetype row has no skill_family (geometry / quadratic pools)
ARCHETYPE_REASONING_FAMILY_LEGACY: Dict[str, str] = {
    "angle_theorem": "tangent_pair_angle",
    "cyclic_angle": "tangent_angle_chase",
    "hidden_theorem": "tangent_length_trap",
    "length_find": "direct_tangent_length",
    "concentric": "concentric_chord",
    "chord_tangent": "chord_perpendicular",
    "secant_tangent": "secant_identify",
    "converse_identify": "conceptual",
    "direct_theorem": "prove_equal_tangents",
    "common_tangent": "common_tangent_length",
    "hots_mixed": "prove_then_compute",
    "tangent_similarity": "power_similarity",
    # Quadratic chapter
    "nature_of_roots": "discriminant_nature",
    "equal_roots_k": "parameter_equal_roots",
    "word_problem_area": "area_quadratic",
    "factorisation_roots": "factorisation",
    "formula_roots": "quadratic_formula",
    "hots_quad": "hots_quadratic_fusion",
}

ARCHETYPE_REASONING_FAMILY: Dict[str, str] = ARCHETYPE_REASONING_FAMILY_LEGACY

# One signature key per paper for hard mode (max 1 unless slot forces teach/reuse)
HARD_PAPER_MAX_PER_SIGNATURE: Dict[str, int] = {
    "tangent_pair:quadrilateral:central_angle": 1,
    "tangent_pair:quadrilateral:angle_between": 1,
    "tangent_pair:quadrilateral:cyclic_angle_chase:central_angle": 1,
    "tangent_pair:cyclic_angle_chase:quadrilateral:central_angle": 1,
    "prove_equal_tangents:pythagoras": 1,
    "direct_tangent_length:pythagoras": 1,
    "tangent_pair:quadrilateral:angle_between:angle_find": 1,
    "tangent_pair:quadrilateral:central_angle:angle_find": 1,
    "tangent_pair:quadrilateral:angle_find": 1,
    "secant_tangent:power_of_point": 2,
    "concentric:chord_touching_inner": 2,
}

SHALLOW_HARD_SIGNATURES = frozenset(
    {
        "tangent_pair:quadrilateral:central_angle",
        "tangent_pair:quadrilateral:angle_between",
        "prove_equal_tangents:pythagoras",
        "direct_tangent_length:pythagoras",
    }
)

L4_L5_FORBIDDEN_SIGNATURES = frozenset(
    {
        "tangent_pair:quadrilateral:central_angle",
        "tangent_pair:quadrilateral:angle_between",
    }
)


def _answer_text(q: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def extract_reasoning_signature(
    stem: str,
    *,
    answer: str = "",
    archetype_id: str = "",
) -> List[str]:
    """Ordered reasoning components (most specific last)."""
    if not stem:
        return []
    low = f"{stem} {answer}".lower()
    sig: List[str] = []

    has_external_pair = bool(
        re.search(
            r"\bfrom\s+[A-Z],?\s*tangents?\s+[A-Z][A-Z]\s+and\s+[A-Z][A-Z]\b",
            stem,
            re.I,
        )
        or re.search(r"\btangents?\s+[A-Z][A-Z]\s+and\s+[A-Z][A-Z]\b", stem, re.I)
    )
    if has_external_pair or "tangents from" in low:
        sig.append("tangent_pair")
    if re.search(
        r"angle\s+[A-Z]{3}\s*=\s*\d+°?",
        stem,
        re.I,
    ) and has_external_pair and re.search(r"find\s+angle\s+[A-Z]O[A-Z]", stem, re.I):
        if not re.search(r"\balternate\b|\bchord\b.*\btangent\b", low):
            sig.append("tangent_pair_angle_sum")

    if re.search(r"\bconcentric\b", low):
        sig.append("concentric")
    if re.search(r"\bchord\b.*\btouch", low) or (
        "chord" in low and "concentric" in low
    ):
        sig.append("chord_touching_inner")
    if re.search(r"\bperpendicular\b.*\bchord\b|\bchord\b.*\bperpendicular\b", low):
        sig.append("chord_perpendicular")
    if re.search(r"\bprove\b.*\bperpendicular\b", low) and "chord" in low:
        sig.append("perpendicular_proof")

    if re.search(r"\bprove\b.*\b([A-Z][A-Z])\s*=\s*([A-Z][A-Z])\b", stem, re.I):
        sig.append("prove_equal_tangents")
    if re.search(r"\bfind\s+(?:the\s+)?(?:length|distance|AP|TA|TP|TQ|PQ)\b", low):
        if "pythagoras" in low or re.search(r"\bOP\s*=\s*\d|\bOT\s*=\s*\d", stem, re.I):
            sig.append("pythagoras")
        sig.append("length_compute")

    if re.search(r"\bmajor\s+arc\b", low) and re.search(
        r"\bfind\s+angle\b", low
    ):
        sig.append("cyclic_angle_chase")
    if re.search(r"\bfind\s+angle\b", low):
        sig.append("angle_find")
        if re.search(r"angle\s+[A-Z]O[A-Z]\b", stem, re.I) and has_external_pair:
            if re.search(r"angle\s+[A-Z][A-Z][A-Z]\s*=\s*\d", stem, re.I):
                if re.search(r"find\s+angle\s+[A-Z]O[A-Z]", stem, re.I):
                    sig.append("central_angle")
                else:
                    sig.append("angle_between")
            elif re.search(r"find\s+angle\s+[A-Z]O[A-Z]", stem, re.I):
                sig.append("central_angle")
            else:
                sig.append("angle_between")
        elif "quadrilateral" in low or "180" in low or "supplementary" in low:
            sig.append("quadrilateral")
        else:
            sig.append("quadrilateral")

    if re.search(r"\bdiscriminant\b|nature\s+of\s+roots", low):
        sig.append("discriminant")
    if re.search(r"\bequal\s+roots\b|find\s+(?:the\s+)?value\s+of\s+k\b", low):
        sig.append("equal_roots_parameter")
    if re.search(r"\bfactoris", low):
        sig.append("factorisation")
    if re.search(r"\barea\b.*\b(?:length|breadth|width)\b|\bbreadth\b.*\barea\b", low):
        sig.append("area_word_problem")
    if re.search(r"\bspeed\b|\bkm/h\b", low) and re.search(r"\btime\b|\bhour\b", low):
        sig.append("speed_time_quadratic")

    if "similar" in low or "cyclic" in low:
        if "cyclic" in low:
            sig.append("cyclic")
        if "similar" in low:
            sig.append("similarity")
    if re.search(r"\bsecant\b", low) and re.search(r"\bTA\s*[·x×]?\s*TD|TC\s*[·x×]?\s*TD", stem, re.I):
        sig.append("power_of_point")
    if re.search(r"\bhence\b.*\bfind\b", low) or (
        re.search(r"\bor\b", stem, re.I) and re.search(r"\bprove\b", low)
    ):
        sig.append("fusion")

    if not sig and archetype_id:
        fam = ARCHETYPE_REASONING_FAMILY.get(archetype_id, archetype_id)
        sig.append(fam)

    # Deduplicate preserving order
    seen: set[str] = set()
    out: List[str] = []
    for s in sig:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def signature_key(components: List[str]) -> str:
    if not components:
        return "generic"
    # Collapse tangent_pair angle variants to one graph key
    normalized = list(components)
    if "tangent_pair" in normalized and "quadrilateral" in normalized:
        if "central_angle" in normalized or "angle_between" in normalized:
            if "central_angle" in normalized:
                normalized = [
                    x
                    for x in normalized
                    if x not in ("angle_between", "angle_find")
                ]
                if "central_angle" not in normalized:
                    normalized.append("central_angle")
            else:
                normalized = [
                    x
                    for x in normalized
                    if x not in ("central_angle",)
                ]
                if "angle_between" not in normalized:
                    normalized.append("angle_between")
    return ":".join(normalized[:6])


def reasoning_signature_for_question(q: Dict[str, Any]) -> str:
    stem = q.get("content") or ""
    arch = q.get("archetype_id") or q.get("slot_archetype") or ""
    comps = extract_reasoning_signature(
        stem, answer=_answer_text(q), archetype_id=arch
    )
    return signature_key(comps)


def annotate_paper_reasoning(
    questions: List[Dict[str, Any]],
    *,
    ui_difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    """Tag each question with reasoning_signature / duplicate flags."""
    keys: List[str] = []
    for q in questions:
        stem = q.get("content") or ""
        comps = extract_reasoning_signature(
            stem,
            answer=_answer_text(q),
            archetype_id=q.get("archetype_id") or "",
        )
        key = signature_key(comps)
        q["reasoning_components"] = comps
        q["reasoning_signature"] = key
        keys.append(key)

    counts = Counter(keys)
    ui = (ui_difficulty or "medium").lower()
    hard = ui in ("hard", "difficult")

    for q, key in zip(questions, keys):
        flags: List[str] = list(q.get("reasoning_flags") or [])
        dup_count = counts[key]
        max_allowed = HARD_PAPER_MAX_PER_SIGNATURE.get(key, 2 if hard else 3)
        if dup_count > max_allowed:
            q["reasoning_duplicate"] = True
            flags.append(f"duplicate_reasoning_graph:{key}")
        if hard and key in SHALLOW_HARD_SIGNATURES:
            flags.append(f"shallow_hard_signature:{key}")
        q["reasoning_flags"] = flags
    return questions


def should_reject_reasoning(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
) -> bool:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return bool(q.get("reasoning_duplicate"))

    if q.get("reasoning_duplicate"):
        return True
    key = q.get("reasoning_signature") or ""
    band = slot_band or "L3"
    if band in ("L4", "L5") and key in L4_L5_FORBIDDEN_SIGNATURES:
        return True
    flags = q.get("reasoning_flags") or []
    if any("duplicate_reasoning_graph" in f for f in flags):
        return True
    if band in ("L4", "L5") and any("shallow_hard_signature" in f for f in flags):
        return True
    return False


def reasoning_diversity_ok(
    questions: List[Dict[str, Any]],
    *,
    ui_difficulty: str = "medium",
    locked_chapter: str = "",
) -> Tuple[bool, str]:
    if len(questions) < 2:
        return True, ""
    annotate_paper_reasoning(questions, ui_difficulty=ui_difficulty)
    dups = sum(1 for q in questions if q.get("reasoning_duplicate"))
    if dups:
        return False, f"reasoning_graph_duplicates:{dups}"
    ui = (ui_difficulty or "medium").lower()
    chapter = (locked_chapter or "").lower()
    if ui in ("hard", "difficult"):
        keys = [q.get("reasoning_signature") for q in questions]
        if chapter == "quadratic":
            area_n = sum(1 for k in keys if k and "area_word" in k)
            if area_n >= 2:
                return False, "duplicate_area_word_quadratic"
            disc_n = sum(1 for k in keys if k and "discriminant" in k)
            if disc_n >= 3:
                return False, "discriminant_cluster_quadratic"
        else:
            tp = sum(
                1
                for k in keys
                if k and k.startswith("tangent_pair:quadrilateral")
            )
            if tp >= 2:
                return False, "tangent_pair_angle_cluster"
            pyth_n = sum(
                1
                for k in keys
                if k and ("pythagoras" in k or k.startswith("direct_tangent_length"))
            )
            if pyth_n >= 2:
                return False, "direct_pythagoras_cluster"
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    pack = get_chapter_rule_pack(chapter)
    if pack.paper_quality and pack.paper_quality.enabled:
        from app.generation.chapter_paper_quality import (
            reasoning_diversity_ok_for_chapter,
        )

        return reasoning_diversity_ok_for_chapter(questions, chapter=chapter)
    return True, ""


def pick_diverse_archetype_ids(
    n: int,
    chapter: str,
    rng,
    *,
    ui_difficulty: str = "medium",
) -> List[str]:
    """Weighted pick with reasoning-family dedup for hard UI."""
    from app.generation.rd_archetypes import (
        CHAPTER_PATTERNS_HARD,
        CHAPTER_PATTERNS,
        _chapter_archetype_pool,
    )

    ui = (ui_difficulty or "medium").lower()
    pool_ids_set = {a["id"] for a in _chapter_archetype_pool(chapter)}
    if ui in ("hard", "difficult"):
        raw = CHAPTER_PATTERNS_HARD.get(chapter, CHAPTER_PATTERNS_HARD.get("generic", []))
    else:
        raw = CHAPTER_PATTERNS.get(chapter, CHAPTER_PATTERNS.get("generic", []))
    weights = [(aid, p) for aid, p in raw if aid in pool_ids_set]
    if not weights:
        weights = [(a["id"], 1.0) for a in _chapter_archetype_pool(chapter)]

    ids = [w[0] for w in weights]
    probs = [w[1] for w in weights]
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    pq = get_chapter_rule_pack(chapter).paper_quality
    capped_families = pq.max_family_dict() if pq and pq.enabled else {}

    chosen: List[str] = []
    used_families: set[str] = set()
    pool_ids, pool_probs = list(ids), list(probs)

    for _ in range(n):
        if not pool_ids:
            pool_ids, pool_probs = list(ids), list(probs)
            used_families.clear()
        candidates = []
        candidate_probs = []
        for aid, p in zip(pool_ids, pool_probs):
            fam = _skill_family_for_archetype(aid)
            if chapter in ("quadrilaterals", "quadratic", "triangles"):
                if fam in ("tangent_pair_angle", "tangent_angle_chase"):
                    continue
            if fam in capped_families and fam in used_families:
                continue
            if ui in ("hard", "difficult") and fam in used_families:
                if fam in ("tangent_pair_angle", "tangent_angle_chase"):
                    continue
            candidates.append(aid)
            candidate_probs.append(p)
        if not candidates:
            candidates, candidate_probs = pool_ids, pool_probs
        pick = rng.choices(candidates, weights=candidate_probs, k=1)[0]
        chosen.append(pick)
        used_families.add(_skill_family_for_archetype(pick))
        if pick in pool_ids:
            idx = pool_ids.index(pick)
            pool_ids.pop(idx)
            pool_probs.pop(idx)
    return chosen


def reasoning_diversity_prompt_block(chapter: str = "generic") -> str:
    from app.generation.chapter_prompt_isolation import (
        reasoning_diversity_prompt_block as _chapter_block,
    )

    return _chapter_block(chapter)
