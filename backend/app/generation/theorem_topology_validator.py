"""
Theorem topology validation — blueprint archetype vs realized reasoning graph.

Prompts suggest complexity; this module rejects items whose stems/answers
collapse to safe NCERT templates (single-step Pythagoras, diagram-only proofs,
disconnected OR branches, archetype mismatch).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.theorem_graph_planner import CIRCLES_THEOREM_GRAPHS

# Stems must name geometric referents — figure assists but cannot be sole carrier
MINIMUM_STEM_REFERENTS: Dict[str, Tuple[str, ...]] = {
    "power_of_point_proof": (
        r"\btangent\b",
        r"\bsecant\b",
    ),
    "equal_tangents_proof": (
        r"\btangents?\b",
        r"\bexternal\s+point\b|from\s+[A-Z]\b",
    ),
    "concentric_chord": (
        r"\bconcentric\b|two\s+circles\b",
        r"\bchord\b",
    ),
}

ARCHETYPE_TOPOLOGY: Dict[str, Dict[str, Any]] = {
    "hidden_theorem": {
        "require_any": (r"\btangents?\b", r"\bexternal\b|from\s+[A-Z],?\s*tangent"),
        "min_answer_steps": 3,
        "families": ("tangent_length_trap", "hidden_theorem"),
    },
    "chord_tangent": {
        "require_any": (r"\bchord\b", r"\bperpendicular\b.*\bchord\b|chord\b.*\bperpendicular\b"),
        "min_answer_steps": 3,
        "families": ("chord_perpendicular", "chord_perpendicular:perpendicular_proof"),
    },
    "concentric": {
        "require_any": (r"\bconcentric\b", r"\btwo\s+circles\b.*\bcentre\b|\bcentre\s+O\b.*\bradii\b"),
        "min_answer_steps": 4,
        "families": ("concentric", "concentric:chord_touching_inner"),
    },
    "tangent_similarity": {
        "require_any": (r"\btangent\b", r"\bsecant\b"),
        "require_all": (),
        "min_answer_steps": 4,
        "families": ("power_similarity", "power_of_point", "similarity"),
    },
    "secant_tangent": {
        "require_any": (r"\btangent\b", r"\bsecant\b"),
        "min_answer_steps": 3,
        "families": ("power_of_point", "power_similarity"),
    },
    "common_tangent": {
        "require_any": (
            r"\bcommon\s+external\s+tangent\b",
            r"\bcentres?\s+O\s+and\s+P\b|\bcenters?\s+O\s+and\s+P\b",
            r"\bradii\b.*\bOP\b",
        ),
        "min_answer_steps": 4,
        "families": ("common_tangent_length",),
    },
    "hots_mixed": {
        "require_any": (r"\bor\b", r"\(i\)", r"\(ii\)"),
        "min_answer_steps": 4,
        "forbid_signatures": (
            "tangent_pair:quadrilateral:central_angle",
            "tangent_pair:quadrilateral:angle_between",
            "direct_tangent_length:pythagoras",
        ),
        "families": ("prove_then_compute", "fusion"),
    },
    "cyclic_angle": {
        "require_any": (r"\b(?:arc|major\s+arc|cyclic|angle\s+[A-Z]{3}.*\bpoint\b)",),
        "min_answer_steps": 4,
        "families": ("tangent_angle_chase", "cyclic"),
    },
}

_L5_FORBIDDEN_SHALLOW = frozenset(
    {
        "tangent_pair:quadrilateral:central_angle",
        "tangent_pair:quadrilateral:angle_between",
        "direct_tangent_length:pythagoras",
        "prove_equal_tangents:pythagoras",
        "tangent_pair:quadrilateral:angle_between:angle_find",
    }
)

_POWER_PROOF_RE = re.compile(
    r"\bprove\s+that\s+[A-Z]{2}\s*(?:\^|²|2)?\s*=\s*[A-Z]{2}\s*(?:[·x×\.]\s*)?[A-Z]{2}\b",
    re.I,
)
_SPARSE_EQUAL_TANGENTS_RE = re.compile(
    r"\bprove\s+that\s+[A-Z]{2}\s*=\s*[A-Z]{2}\b",
    re.I,
)


def _stem_text(q: Dict[str, Any]) -> str:
    return (q.get("content") or q.get("question") or "").strip()


def _answer_text(q: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def _count_answer_steps(answer: str) -> int:
    if not answer:
        return 0
    return len(re.findall(r"\bstep\s*\d+\b", answer, re.I))


def _is_direct_tangent_pythagoras(stem: str) -> bool:
    low = stem.lower()
    if re.search(r"\(i\)|\(ii\)|prove.*bisect|concentric|chord\b.*\b(?:length|midpoint)", low):
        return False
    if re.search(
        r"\bfind\s+(?:AP|TA|TP|TQ|PQ|KJ|EY|UW|FC|LA|GR|HX|KJ)\b",
        stem,
        re.I,
    ) and re.search(r"\bO[A-Z]\s*=\s*\d", stem, re.I):
        if re.search(r"\bradius\b|O[A-Z]\s*=\s*\d.*\bcm\b", stem, re.I):
            return True
    if re.search(r"\bfind\s+[A-Z]{2}\b", stem) and re.search(
        r"\bO[A-Z]\s*=\s*\d", stem
    ):
        if re.search(r"\btangent\b", low) and not re.search(
            r"\bsecant\b|\bchord\b.*\b(?:prove|bisect)", low
        ):
            return True
    return False


def _disconnected_or_branches(stem: str) -> bool:
    low = stem.lower()
    if "**or**" not in low and re.search(r"\bor\b", low) is None:
        return False
    has_angle = bool(
        re.search(r"\bfind\s+angle\b", low)
        or re.search(r"\bfind\s+[A-Z]{3}\b", stem, re.I)
        and re.search(r"angle\s+[A-Z]{3}\s*=", stem, re.I)
    )
    has_pyth = bool(
        re.search(r"\b(?:find|hence\s+find)\s+[A-Z]{2}\b", stem, re.I)
        and re.search(r"\bO[A-Z]\s*=\s*\d", stem, re.I)
    )
    has_prove_len = bool(re.search(r"\bprove\b.*\b(?:hence\s+)?find\b", low))
    return has_angle and (has_pyth or has_prove_len)


def validate_minimum_stem_referents(q: Dict[str, Any]) -> Dict[str, Any]:
    """Figure may assist; theorem structure must exist in the stem text."""
    stem = _stem_text(q)
    low = stem.lower()
    flags: List[str] = []
    score = 1.0

    if not stem:
        return {
            "stem_referents_ok": False,
            "stem_referent_flags": ["empty_stem"],
            "stem_referent_score": 0.0,
        }

    if _POWER_PROOF_RE.search(stem):
        if not (re.search(r"\btangent\b", low) and re.search(r"\bsecant\b", low)):
            flags.append("diagram_only_power_of_point")
            score -= 0.55

    if _SPARSE_EQUAL_TANGENTS_RE.search(stem) and not re.search(
        r"\btangents?\b.*\bexternal\b|from\s+[A-Z]\b.*\btangents?\b",
        stem,
        re.I,
    ):
        if not re.search(r"\btangents?\s+[A-Z]{2}\b", stem, re.I):
            flags.append("diagram_only_equal_tangents_proof")
            score -= 0.45

    if q.get("question_type") == "FigureBased" or q.get("type") == "FigureBased":
        if re.search(r"\bprove\b", low) and len(stem.split()) < 12:
            if _POWER_PROOF_RE.search(stem) or _SPARSE_EQUAL_TANGENTS_RE.search(stem):
                flags.append("sparse_proof_under_specified")
                score -= 0.35

    ref_score = max(0.0, min(1.0, score))
    critical = {
        "diagram_only_power_of_point",
        "diagram_only_equal_tangents_proof",
    }
    return {
        "stem_referent_score": round(ref_score, 3),
        "stem_referent_flags": flags,
        "stem_referents_ok": ref_score >= 0.62
        and not any(f in critical for f in flags),
    }


def validate_slot_topology(
    q: Dict[str, Any],
    *,
    slot_meta: Optional[Dict[str, Any]] = None,
    ui_difficulty: str = "medium",
) -> Dict[str, Any]:
    """Match blueprint archetype to stem/answer topology."""
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return {"topology_ok": True, "topology_flags": [], "topology_score": 1.0}

    stem = _stem_text(q)
    answer = _answer_text(q)
    meta = slot_meta or {}
    archetype = (
        meta.get("archetype_id")
        or q.get("archetype_id")
        or q.get("slot_archetype")
        or ""
    ).strip()
    band = meta.get("band") or q.get("slot_band") or "L3"
    flags: List[str] = []
    score = 1.0

    if _is_direct_tangent_pythagoras(stem):
        flags.append("topology_direct_pythagoras_only")
        score -= 0.5
        if band in ("L3", "L4", "L5") and not meta.get("allow_direct_length"):
            flags.append(f"forbidden_single_step_pythagoras_{band}")

    if _disconnected_or_branches(stem) and band in ("L4", "L5"):
        flags.append("topology_disconnected_or")
        score -= 0.4

    spec = ARCHETYPE_TOPOLOGY.get(archetype, {})
    if spec:
        req_any = spec.get("require_any") or ()
        if req_any and not any(re.search(p, stem, re.I) for p in req_any):
            flags.append(f"archetype_stem_mismatch:{archetype}")
            score -= 0.45
        min_steps = spec.get("min_answer_steps", 3)
        if band in ("L4", "L5") and _count_answer_steps(answer) < min_steps:
            flags.append(f"answer_steps_below_{min_steps}_for_{archetype}")
            score -= 0.3
        sig = q.get("reasoning_signature") or ""
        forbid_sigs = spec.get("forbid_signatures") or ()
        if sig in forbid_sigs or any(s in sig for s in forbid_sigs):
            flags.append(f"shallow_signature_for_{archetype}")
            score -= 0.45

    if band == "L5":
        sig = q.get("reasoning_signature") or ""
        if sig in _L5_FORBIDDEN_SHALLOW or (
            sig.startswith("tangent_pair:") and "pythagoras" not in sig
        ):
            if archetype not in ("hots_mixed", "cyclic_angle", "tangent_similarity"):
                if sig in _L5_FORBIDDEN_SHALLOW:
                    flags.append("l5_shallow_topology")
                    score -= 0.5
        if meta.get("hots") or archetype == "hots_mixed":
            if not (
                re.search(r"\bhence\b", answer, re.I)
                or q.get("fusion_count", 0) >= 1
                or _count_answer_steps(answer) >= 5
            ):
                flags.append("hots_fusion_not_realized")
                score -= 0.4

    # Planned graph steps should appear in answer (soft check)
    planned = CIRCLES_THEOREM_GRAPHS.get(archetype, ())
    if planned and band in ("L4", "L5"):
        ans_low = answer.lower()
        if archetype == "concentric" and "perpendicular" not in ans_low:
            flags.append("missing_concentric_bisect_chain")
            score -= 0.25
        if archetype == "tangent_similarity" and not (
            "similar" in ans_low or "power" in ans_low or "×" in answer or "·" in answer
        ):
            flags.append("missing_similarity_or_power_chain")
            score -= 0.3

    topo_score = max(0.0, min(1.0, score))
    critical = (
        "topology_direct_pythagoras_only",
        "diagram_only_power_of_point",
        "archetype_stem_mismatch",
        "l5_shallow_topology",
        "hots_fusion_not_realized",
        "topology_disconnected_or",
    )
    return {
        "topology_score": round(topo_score, 3),
        "topology_flags": flags,
        "topology_ok": topo_score >= 0.55
        and not any(
            f == c or f.startswith(c) for f in flags for c in critical
        ),
    }


def should_reject_topology(
    q: Dict[str, Any],
    *,
    slot_meta: Optional[Dict[str, Any]] = None,
    ui_difficulty: str = "medium",
) -> bool:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return False
    if "stem_referents_ok" not in q:
        q.update(validate_minimum_stem_referents(q))
    if "topology_ok" not in q:
        q.update(
            validate_slot_topology(
                q, slot_meta=slot_meta, ui_difficulty=ui_difficulty
            )
        )
    if not q.get("stem_referents_ok", True):
        return True
    if not q.get("topology_ok", True):
        return True
    flags = (q.get("topology_flags") or []) + (q.get("stem_referent_flags") or [])
    reject_prefixes = (
        "topology_direct_pythagoras",
        "forbidden_single_step",
        "diagram_only_",
        "archetype_stem_mismatch",
        "l5_shallow_topology",
        "hots_fusion_not_realized",
        "topology_disconnected_or",
    )
    return any(
        any(f.startswith(p) or p in f for p in reject_prefixes) for f in flags
    )
