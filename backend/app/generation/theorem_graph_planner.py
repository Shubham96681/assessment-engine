"""
Pre-generation theorem graph hints — slot plans carry inference chains before LLM synthesis.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# archetype_id → ordered theorem / inference steps (answers may name theorems; stems may not)
CIRCLES_THEOREM_GRAPHS: Dict[str, Tuple[str, ...]] = {
    "length_find": (
        "radius ⟂ tangent at contact",
        "right triangle centre–contact–external",
        "Pythagoras on tangent length",
    ),
    "angle_theorem": (
        "radius ⟂ tangent at each contact",
        "isosceles triangle on equal tangents",
        "quadrilateral angle sum → central angle",
    ),
    "hidden_theorem": (
        "equal tangents from external point",
        "radius ⟂ tangent",
        "Pythagoras (trap invisible in stem)",
    ),
    "concentric": (
        "inner radius ⟂ chord at contact",
        "perpendicular from centre bisects chord",
        "Pythagoras on half-chord",
    ),
    "secant_tangent": (
        "radius ⟂ tangent",
        "tangent–secant power EA² = EB·EC",
        "optional Pythagoras check in OAE",
    ),
    "chord_tangent": (
        "radius ⟂ tangent",
        "perpendicular from centre to chord",
        "chord bisection + length find",
    ),
    "cyclic_angle": (
        "radius ⟂ tangents",
        "angle between tangents ↔ arc/central angle",
        "cyclic quadrilateral angle chase",
    ),
    "tangent_similarity": (
        "radius ⟂ tangent",
        "similar triangles from secant configuration",
        "tangent–secant power or proportion",
    ),
    "common_tangent": (
        "parallel radii to contact points",
        "right trapezoid / Pythagoras on offset",
        "external tangent length",
    ),
    "hots_mixed": (
        "disguised reuse of earlier slot theorem (new labels)",
        "hidden dependency before numeric find",
        "Hence chain — NOT independent OR branches",
    ),
    "converse_identify": (
        "definition tangent vs secant",
        "single-step justification or minimal proof",
    ),
    "direct_theorem": (
        "RHS congruence on tangent triangles",
        "CPCT equal tangents",
    ),
}

QUADRATIC_THEOREM_GRAPHS: Dict[str, Tuple[str, ...]] = {
    "factorisation_roots": ("standard form", "factor", "zero product → roots"),
    "nature_of_roots": ("D = b² − 4ac", "sign of D → nature", "optional roots"),
    "equal_roots_k": ("D = 0", "solve for k", "verify double root"),
    "word_problem_area": ("form ax² + bx + c = 0", "factor or formula", "reject invalid dimension"),
    "hots_quad": ("parameter or OR branch", "discriminant or identity", "Hence numeric answer"),
}


def plan_theorem_graph(archetype_id: str, chapter: str) -> str:
    """One-line DAG summary for prompt injection."""
    from app.generation.archetype_registry import normalize_archetype_id

    ch = (chapter or "generic").strip().lower()
    aid = normalize_archetype_id(archetype_id, ch)
    steps: Tuple[str, ...] = ()
    if ch == "circles":
        steps = CIRCLES_THEOREM_GRAPHS.get(aid, ())
    elif ch == "quadratic":
        steps = QUADRATIC_THEOREM_GRAPHS.get(aid, ())
    if not steps:
        return ""
    return " → ".join(steps)


def blueprint_theorem_graph_section(slots: List, chapter: str) -> str:
    """Compact pre-generation graph block for QUESTION prompt."""
    lines = [f"THEOREM GRAPH PLAN — {chapter} (realize these chains in answers):"]
    for s in slots:
        slot_num = getattr(s, "slot", None) or (s.get("slot") if isinstance(s, dict) else 0)
        aid = getattr(s, "archetype_id", None) or (s.get("archetype_id") if isinstance(s, dict) else "")
        graph = plan_theorem_graph(str(aid or ""), chapter)
        if graph:
            lines.append(f'  Q{slot_num}: [{aid}] {graph}')
    if len(lines) <= 1:
        return ""
    return "\n".join(lines)
