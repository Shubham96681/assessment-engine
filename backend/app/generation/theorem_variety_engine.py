"""
Theorem variety + semantic equivalence — reject duplicate reasoning structures.

Embedding dedup catches paraphrase; this module catches same theorem graph with
relabelled points/numbers (e.g. two tangent-pair angle-sum items).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from app.generation.reasoning_signature import (
    extract_reasoning_signature,
    reasoning_signature_for_question,
    signature_key,
)

# Coarse theorem families for Circles papers (spread required on full-hard 10-Q)
CIRCLES_THEOREM_FAMILIES: Tuple[str, ...] = (
    "tangent_radius_perpendicular",
    "concentric_chord",
    "secant_tangent_power",
    "tangent_lengths_equal",
    "common_external_tangent",
    "angle_in_alternate_segment",
    "tangent_pair_central_angle",
    "cyclic_quadrilateral",
    "similar_triangles_tangent",
    "chord_distance_equal",
    "prove_then_compute_fusion",
)

# Max items sharing the same equivalence bucket on a 10-question full-hard paper
FULL_HARD_MAX_PER_EQUIVALENCE: Dict[str, int] = {
    "tangent_pair:quadrilateral:central_angle": 1,
    "tangent_pair:quadrilateral:angle_between": 1,
    "tangent_pair:quadrilateral:angle_find": 1,
    "secant_tangent:power_of_point": 2,
    "direct_tangent_length:pythagoras": 1,
    "prove_equal_tangents:pythagoras": 1,
    "concentric:chord_touching_inner": 2,
    "common_tangent_length": 1,
    "angle_alternate_segment": 1,
}

MIN_DISTINCT_FAMILIES_10Q = 6

# Step 3 — enforced bucket distribution (min, max) per 10-question Circles full-hard paper
CIRCLES_PAPER_BUCKETS: Dict[str, Tuple[int, int]] = {
    "tangent_perpendicular_proof": (1, 1),
    "concentric_chord": (1, 2),
    "secant_tangent_power": (1, 2),
    "tangent_lengths_equal": (1, 2),
    "common_external_tangent": (1, 1),
    "alternate_segment_angle": (1, 1),
    "tangent_pair_central_angle": (0, 1),
    "cyclic_or_similarity": (1, 1),
    "proof_based": (2, 4),
    "fusion_hots": (1, 2),
}

# Slot → required bucket (10-Q full-hard Circles blueprint)
CIRCLES_10_SLOT_BUCKETS: Tuple[str, ...] = (
    "concentric_chord",           # Q1
    "secant_tangent_power",       # Q2 depends Q1
    "tangent_perpendicular_proof",  # Q3
    "common_external_tangent",    # Q4
    "fusion_hots",                # Q5
    "tangent_lengths_equal",      # Q6
    "cyclic_or_similarity",       # Q7 — NOT duplicate tangent-pair angle
    "alternate_segment_angle",    # Q8
    "proof_based",                # Q9 LongAnswer
    "secant_tangent_power",       # Q10 standalone (max 2 in paper)
)


def map_question_to_bucket(q: Dict[str, Any]) -> str:
    """Assign question to distribution bucket for variety enforcement."""
    parts = (q.get("canonical_signature_parts") or {})
    if parts:
        pt = parts.get("primary_theorem", "")
        if pt == "concentric_chord_theorem":
            return "concentric_chord"
        if pt == "tangent_perpendicular_radius":
            return "tangent_perpendicular_proof"
        if pt == "equal_tangents_theorem":
            return "tangent_lengths_equal"
        if pt == "secant_tangent_power":
            return "secant_tangent_power"
        if pt == "common_external_tangent":
            return "common_external_tangent"
        if pt == "tangent_chord_angle_theorem":
            return "alternate_segment_angle"
        if pt == "tangent_pair_angle_sum":
            return "tangent_pair_central_angle"
        if pt in ("cyclic_quadrilateral_angle",):
            return "cyclic_or_similarity"
        if "similar" in pt:
            return "cyclic_or_similarity"
    fams = q.get("theorem_families_inferred") or infer_theorem_families(q)
    if "prove_then_compute_fusion" in fams or "fusion" in str(q.get("archetype_id", "")):
        return "fusion_hots"
    if "concentric_chord" in fams:
        return "concentric_chord"
    if "secant_tangent_power" in fams:
        return "secant_tangent_power"
    if "tangent_lengths_equal" in fams:
        return "tangent_lengths_equal"
    if "common_external_tangent" in fams:
        return "common_external_tangent"
    if "angle_in_alternate_segment" in fams:
        return "alternate_segment_angle"
    if "tangent_pair_central_angle" in fams:
        return "tangent_pair_central_angle"
    if "cyclic_quadrilateral" in fams or "similar_triangles_tangent" in fams:
        return "cyclic_or_similarity"
    if re.search(r"\bprove\b", (q.get("content") or "").lower()):
        return "proof_based"
    return "proof_based"


def validate_bucket_distribution(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    full_hard: bool = False,
) -> Tuple[bool, List[str]]:
    """Enforce CIRCLES_PAPER_BUCKETS min/max counts."""
    if chapter != "circles" or not full_hard or len(questions) < 8:
        return True, []
    from app.generation.canonical_question_signature import annotate_canonical_signatures

    annotate_canonical_signatures(questions)
    annotate_theorem_families(questions)
    counts: Dict[str, int] = {b: 0 for b in CIRCLES_PAPER_BUCKETS}
    for q in questions:
        b = map_question_to_bucket(q)
        counts[b] = counts.get(b, 0) + 1
    issues: List[str] = []
    for bucket, (lo, hi) in CIRCLES_PAPER_BUCKETS.items():
        n = counts.get(bucket, 0)
        if n < lo:
            issues.append(f"bucket_under:{bucket}:{n}<{lo}")
        if n > hi:
            issues.append(f"bucket_over:{bucket}:{n}>{hi}")
    return (not issues), issues


def slot_bucket_directive(
    slot_index: int,
    question_count: int = 10,
    *,
    chapter: str = "circles",
    paper_template_id: Optional[str] = None,
) -> str:
    """Prompt line for file-agent / compiler: slot role + optional topic bucket."""
    from app.generation.paper_templates import (
        resolve_paper_template,
        slot_role_directive,
    )

    if chapter != "circles" and not paper_template_id:
        return ""
    tmpl = resolve_paper_template(
        override=paper_template_id,
        chapter=chapter,
        question_count=question_count,
        ui_difficulty="hard",
        full_hard=question_count <= 5,
    )
    return slot_role_directive(
        slot_index, template=tmpl, chapter=chapter, question_count=question_count
    )


def _answer_text(q: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def infer_theorem_families(q: Dict[str, Any]) -> List[str]:
    """Map question → coarse theorem families (tags + stem heuristics)."""
    tags = [str(t).lower() for t in (q.get("theorem_tags") or [])]
    families: List[str] = []
    for t in tags:
        if t in CIRCLES_THEOREM_FAMILIES:
            families.append(t)
        elif "concentric" in t:
            families.append("concentric_chord")
        elif "secant" in t or "power" in t:
            families.append("secant_tangent_power")
        elif "alternate" in t:
            families.append("angle_in_alternate_segment")
        elif "common" in t and "tangent" in t:
            families.append("common_external_tangent")
        elif "equal" in t and "tangent" in t:
            families.append("tangent_lengths_equal")
        elif "perpendicular" in t or "radius" in t:
            families.append("tangent_radius_perpendicular")

    stem = (q.get("content") or q.get("question") or "").lower()
    ans = _answer_text(q).lower()
    blob = f"{stem} {ans}"
    arch = (q.get("archetype_id") or "").lower()

    if "concentric" in blob or arch == "concentric":
        if "concentric_chord" not in families:
            families.append("concentric_chord")
    if re.search(r"\bsecant\b", blob) and re.search(
        r"ta\s*[²^2]|tc\s*·|×\s*td|power", blob, re.I
    ):
        if "secant_tangent_power" not in families:
            families.append("secant_tangent_power")
    if re.search(r"\bprove\b.*\b(?:jl|jm|pa|pb|rc|rd)\s*=\s*", stem, re.I):
        if "tangent_lengths_equal" not in families:
            families.append("tangent_lengths_equal")
    if "common" in blob and "external" in blob:
        families.append("common_external_tangent")
    if re.search(r"angle\s+\w+\s*=\s*\d+°?", stem) and re.search(
        r"tangent.*chord|chord.*tangent", blob
    ):
        families.append("angle_in_alternate_segment")
    if re.search(r"tangents?\s+[A-Z]{2}\s+and\s+[A-Z]{2}", q.get("content") or "", re.I):
        if re.search(r"find\s+angle\s+[A-Z]O[A-Z]", q.get("content") or "", re.I):
            families.append("tangent_pair_central_angle")
    if re.search(r"\bhence\b", blob) and (
        arch in ("hidden_theorem", "hots_mixed", "direct_theorem")
        or "fusion" in blob
    ):
        families.append("prove_then_compute_fusion")
    if "cyclic" in blob:
        families.append("cyclic_quadrilateral")
    if "similar" in blob:
        families.append("similar_triangles_tangent")

    seen: set[str] = set()
    out: List[str] = []
    for f in families:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def theorem_equivalence_key(q: Dict[str, Any]) -> str:
    """
    Label- and number-insensitive reasoning bucket.
    Two items with the same key are theorem-equivalent duplicates.
    """
    stem = q.get("content") or q.get("question") or ""
    arch = (q.get("archetype_id") or q.get("slot_archetype") or "generic").lower()
    comps = extract_reasoning_signature(
        stem,
        answer=_answer_text(q),
        archetype_id=arch,
    )
    rs = signature_key(comps)

    families = tuple(sorted(infer_theorem_families(q)))
    fam_key = "+".join(families[:4]) if families else "none"

    low = stem.lower()
    op = "generic"
    if re.search(r"\bconcentric\b", low) and re.search(r"\bchord\b", low):
        op = "concentric_chord_find"
    elif re.search(r"\bprove\b", low) and re.search(r"\bperpendicular\b", low):
        op = "perp_radius_proof"
    elif re.search(r"\bsecant\b", low) and re.search(r"\btangent\b", low):
        op = "secant_tangent_power"
    elif re.search(r"\bprove\b", low) and re.search(r"\b=\s*[A-Z]{2}\b", stem, re.I):
        op = "prove_equal_tangents"
    elif re.search(r"common\s+external\s+tangent|direct\s+common", low):
        op = "common_external_tangent"
    elif re.search(r"tangents?\s+[A-Z]{2}", stem, re.I) and re.search(
        r"find\s+angle", low
    ):
        op = "tangent_pair_angle_sum"
    elif re.search(r"tangent.*chord|chord.*tangent", low) and re.search(
        r"find\s+angle", low
    ):
        op = "alternate_segment_angle"
    elif re.search(r"\btangent\b", low) and re.search(r"\bfind\b", low) and re.search(
        r"\bradius\b|distance.*centre|distance.*center", low
    ):
        op = "tangent_length_find_radius"

    cog = (q.get("cognitive_type") or "compute").lower()
    # Primary dedup bucket — ignore tag noise and relabelled numbers
    return f"{arch}|{op}|{rs}|{cog}"


def annotate_theorem_families(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for q in questions:
        fams = infer_theorem_families(q)
        q["theorem_families_inferred"] = fams
        q["theorem_equivalence_key"] = theorem_equivalence_key(q)
    return questions


def filter_theorem_equivalence_duplicates(
    questions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Drop later items that share a theorem-equivalence bucket with an earlier item."""
    if not questions:
        return []
    annotate_theorem_families(questions)
    kept: List[Dict[str, Any]] = []
    keys: List[str] = []
    for q in questions:
        key = q.get("theorem_equivalence_key") or theorem_equivalence_key(q)
        if key in keys:
            q["dedup_reason"] = f"theorem_equivalence_duplicate:{key}"
            continue
        keys.append(key)
        kept.append(q)
    if not kept and questions:
        q0 = dict(questions[0])
        q0["dedup_warning"] = "all_theorem_equivalent_kept_one"
        return [q0]
    return kept


def validate_paper_theorem_variety(
    questions: List[Dict[str, Any]],
    *,
    locked_chapter: str = "",
    full_hard: bool = False,
    question_count: int = 0,
) -> Tuple[bool, List[str]]:
    """Paper-level spread checks for hard Circles assessments."""
    issues: List[str] = []
    if not questions:
        return False, ["empty_paper"]
    ch = (locked_chapter or "").lower()
    n = question_count or len(questions)
    annotate_theorem_families(questions)

    eq_keys = [q.get("theorem_equivalence_key") or "" for q in questions]
    eq_counts = Counter(eq_keys)
    for key, cnt in eq_counts.items():
        if not key or cnt < 2:
            continue
        parts = key.split("|")
        rs_part = parts[2] if len(parts) > 2 else key
        op_part = parts[1] if len(parts) > 1 else ""
        max_allowed = FULL_HARD_MAX_PER_EQUIVALENCE.get(
            rs_part,
            FULL_HARD_MAX_PER_EQUIVALENCE.get(op_part, 1 if full_hard else 2),
        )
        if cnt > max_allowed:
            issues.append(f"theorem_equivalence_cluster:{key}:{cnt}>{max_allowed}")

    if ch == "circles" and full_hard and n >= 8:
        all_fams: List[str] = []
        for q in questions:
            all_fams.extend(q.get("theorem_families_inferred") or [])
        distinct = len(set(all_fams))
        if distinct < MIN_DISTINCT_FAMILIES_10Q:
            issues.append(
                f"low_theorem_family_spread:{distinct}<{MIN_DISTINCT_FAMILIES_10Q}"
            )
        tp_angle = sum(
            1
            for q in questions
            if "tangent_pair_central_angle" in (q.get("theorem_families_inferred") or [])
        )
        if tp_angle >= 2:
            issues.append(f"tangent_pair_angle_duplicate:{tp_angle}")
        secant_n = sum(
            1
            for q in questions
            if "secant_tangent_power"
            in (q.get("theorem_families_inferred") or [])
            and "concentric_chord"
            not in (q.get("theorem_families_inferred") or [])
        )
        if secant_n >= 3:
            issues.append(f"secant_tangent_overuse:{secant_n}")

    rs_keys = [reasoning_signature_for_question(q) for q in questions]
    rs_counts = Counter(rs_keys)
    for rk, cnt in rs_counts.items():
        if cnt >= 2 and rk.startswith("tangent_pair:quadrilateral"):
            issues.append(f"duplicate_reasoning_graph:{rk}:{cnt}")

    if ch == "circles" and full_hard and n >= 8:
        bucket_ok, bucket_issues = validate_bucket_distribution(
            questions, chapter=ch, full_hard=full_hard
        )
        if not bucket_ok:
            issues.extend(bucket_issues)

    return (not issues), issues


def mark_theorem_equivalence_duplicates(
    questions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Flag 2nd+ items in the same equivalence bucket (for quality rejection)."""
    annotate_theorem_families(questions)
    seen: set[str] = set()
    for q in questions:
        key = q.get("theorem_equivalence_key") or ""
        if key in seen:
            q["theorem_equivalent_duplicate"] = True
            flags = list(q.get("reasoning_flags") or [])
            flags.append(f"theorem_equivalence_duplicate:{key}")
            q["reasoning_flags"] = flags
        elif key:
            seen.add(key)
    return questions


def theorem_variety_prompt_block(
    chapter: str = "circles",
    question_count: int = 10,
    *,
    paper_template_id: Optional[str] = None,
    ui_difficulty: str = "hard",
    full_hard: bool = False,
) -> str:
    from app.generation.paper_templates import (
        resolve_paper_template,
        template_slot_assignments_block,
    )

    if chapter != "circles" and not paper_template_id:
        return ""
    tmpl = resolve_paper_template(
        override=paper_template_id,
        chapter=chapter,
        question_count=question_count,
        ui_difficulty=ui_difficulty,
        full_hard=full_hard,
    )
    base = f"""
THEOREM VARIETY ENGINE (mandatory — {question_count} questions):
- Each item must use a DISTINCT reasoning structure — not the same theorem with new labels.
- MAX ONE: tangent-pair → 180° − angle → central angle (shallow NCERT drill).
- MAX TWO: standalone secant–tangent power (dependency Q2 counts as one).
- MAX ONE: direct tangent-length → radius find without fusion.
- Spread across ≥6 families: concentric chord, ⟂ radius proof, common external tangent,
  equal tangents proof+Hence, alternate segment, cyclic/similarity, fusion HOTS.
- BAN publishing two items whose only change is point names and integers.
- ZERO duplicate canonical signatures per paper (primary_theorem + reasoning_pattern + answer_structure + diagram_archetype).
""".strip()
    if question_count >= 10 and tmpl.id == "chained_concentric":
        slots = "\n".join(
            f"  Q{i+1}: {CIRCLES_10_SLOT_BUCKETS[i]}"
            for i in range(min(10, len(CIRCLES_10_SLOT_BUCKETS)))
        )
        base += f"\nSLOT BUCKET ASSIGNMENTS (mandatory):\n{slots}"
    else:
        block = template_slot_assignments_block(tmpl, question_count, chapter=chapter)
        if block:
            base += f"\n{block}"
    return base.strip()
