"""
Recompute model answers from question stems — single source of truth for answer keys.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.common_tangent_values import (
    external_tangent_length,
    parse_external_tangent_givens,
)
from app.generation.concentric_values import parse_concentric_radii
from app.generation.fusion_q5_values import parse_fusion_givens
from app.generation.question_pipeline import finalize_question_dict
from app.generation.question_text import fix_secant_answer_variables

_PA_RE = re.compile(r"\bPA\s*=\s*(\d+(?:\.\d+)?)\s*cm", re.I)
_PQ_RE = re.compile(r"\bPQ\s*=\s*(\d+(?:\.\d+)?)\s*cm", re.I)
_GJ_RE = re.compile(r"\bGJ\s*=\s*(\d+(?:\.\d+)?)\s*cm", re.I)
_OG_FROM_O_RE = re.compile(
    r"\bpoint\s+G\s+is\s+(\d+(?:\.\d+)?)\s*cm\s+from\s+O\b",
    re.I,
)


def _int(x: float) -> int:
    return int(round(x))


def _sqrt_text(n: float, *, suffix: str = " cm") -> str:
    n = max(0.0, n)
    root = math.isqrt(int(round(n)))
    if abs(root * root - n) < 1e-6:
        return f"√{root}{suffix}"
    return f"√{int(round(n))}{suffix}"


def build_concentric_answer(outer: float, inner: float) -> str:
    r, r_in = max(outer, inner), min(outer, inner)
    diff = r * r - r_in * r_in
    half = math.isqrt(int(round(diff)))
    de = 2 * half
    return (
        f"Given: inner radius OF = {_int(r_in)} cm, outer radius OD = {_int(r)} cm; "
        f"chord DE touches the inner circle at F. "
        f"Step 1: DE is tangent to the inner circle at F, so OF is perpendicular to DE (Theorem 10.1). "
        f"Step 2: A perpendicular from the centre to a chord bisects it, so F is the midpoint of DE. "
        f"Step 3: In right triangle OFD, DF² = {_int(r)}² − {_int(r_in)}² = {_int(diff)}. "
        f"Step 4: DF = {half} cm, hence DE = 2DF = {de} cm. "
        f"Step 5: Therefore DE = {de} cm."
    )


def build_tangent_secant_answer(pa: float, pq: float, *, outer_r: Optional[float] = None) -> str:
    pa_i, pq_i = _int(pa), _int(pq)
    pr = (pa_i * pa_i) // pq_i if pq_i else 0
    intro = (
        f"From Question 1, outer radius OA = {_int(outer_r)} cm. "
        if outer_r
        else ""
    )
    return (
        f"{intro}"
        f"Step 1: On the outer circle, tangent–secant power gives PA² = PQ × PR. "
        f"Step 2: With PA = {pa_i} cm and PQ = {pq_i} cm, {pa_i * pa_i} = {pq_i} × PR. "
        f"Step 3: Hence PR = {pr} cm. "
        f"Step 4: Check PQ × PR = {pq_i} × {pr} = {pq_i * pr} = PA². "
        f"Step 5: Therefore PR = {pr} cm."
    )


def build_external_tangent_answer(
    r_small: float, r_large: float, dist: float, c1: str = "G", c2: str = "H"
) -> str:
    rs, rl, d_i = _int(r_small), _int(r_large), _int(dist)
    diff = rl - rs
    ef_sq = d_i * d_i - diff * diff
    ef = int(round(external_tangent_length(rs, rl, d_i)))
    ef_disp = str(ef) if abs(ef * ef - ef_sq) < 1 else _sqrt_text(ef_sq, suffix="")
    return (
        f"Given: radii {rs} cm and {rl} cm, centre distance {c1}{c2} = {d_i} cm. "
        f"Step 1: For a direct common external tangent, use offset ({rl} − {rs}) = {diff} cm along {c1}{c2}. "
        f"Step 2: Right triangle with hypotenuse {d_i} cm and leg {diff} cm. "
        f"Step 3: Tangent length = √({d_i}² − {diff}²) = {ef_disp} cm. "
        f"Step 4: Parallel radii to contact points form a right trapezoid with the same tangent segment. "
        f"Step 5: Hence the direct common external tangent has length {ef_disp} cm."
    )


def build_fusion_answer(
    outer_r: float,
    pa: float,
    og: float,
    gj: float,
) -> str:
    r, pa_i, og_i, gj_i = _int(outer_r), _int(pa), _int(og), _int(gj)
    op_sq = r * r + pa_i * pa_i
    gh_sq = og_i * og_i - r * r
    gk = gh_sq // gj_i if gj_i else 0
    gh = math.isqrt(max(0, int(gh_sq)))
    return (
        f"From Question 1, outer radius OA = {r} cm. From Question 2, PA = {pa_i} cm and OA ⟂ PA at A. "
        f"(i) Step 1: In right triangle OPA, OP² = OA² + PA² = {r}² + {pa_i}² = {op_sq}. "
        f"Step 2: Hence OP = {_sqrt_text(op_sq, suffix=' cm')}. "
        f"(ii) Step 3: For G with OG = {og_i} cm, tangent GH satisfies GH² = OG² − OA² = {og_i}² − {r}² = {gh_sq}. "
        f"Step 4: Secant power gives GH² = GJ × GK; {gh_sq} = {gj_i} × GK. "
        f"Step 5: Hence GK = {gk} cm and GH = {gh} cm; check {gj_i} × {gk} = {gj_i * gk} = GH²."
    )


def build_converse_tangent_proof_answer() -> str:
    return (
        "Given: line through S meets the circle only at S; OS is perpendicular to the line at S. "
        "Step 1: Suppose the line meets the circle again at a second point T ≠ S. "
        "Step 2: OS is perpendicular to the line, so OT < OS, placing T inside the circle — impossible. "
        "Step 3: Hence the line meets the circle only at S. "
        "Step 4: A line through a point on a circle and perpendicular to the radius at that point is tangent. "
        "Step 5: Therefore the line is tangent to the circle at S."
    )


def _slot_index(q: Dict[str, Any], fallback: int) -> int:
    sn = q.get("slot_number")
    if sn is not None and int(sn) >= 1:
        return int(sn)
    return fallback


def sync_answer_for_slot(
    q: Dict[str, Any],
    slot: int,
    *,
    chapter: str,
    q1_stem: str = "",
    q2_stem: str = "",
) -> Dict[str, Any]:
    """Rewrite correct_answer (and short explanation) from current stem values."""
    out = dict(q)
    stem = (out.get("content") or out.get("question") or "").strip()
    if not stem or chapter != "circles":
        return finalize_question_dict(out)

    outer_r = None
    pa_len = None
    if q1_stem:
        parsed = parse_concentric_radii(q1_stem)
        if parsed:
            outer_r = parsed[0]
    if q2_stem:
        pa_m = _PA_RE.search(q2_stem)
        if pa_m:
            pa_len = float(pa_m.group(1))

    new_ans: Optional[str] = None
    if slot == 1:
        parsed = parse_concentric_radii(stem)
        if parsed:
            new_ans = build_concentric_answer(parsed[0], parsed[1])
    elif slot == 2:
        pa_m = _PA_RE.search(stem)
        pq_m = _PQ_RE.search(stem)
        if pa_m and pq_m:
            new_ans = build_tangent_secant_answer(
                float(pa_m.group(1)),
                float(pq_m.group(1)),
                outer_r=outer_r,
            )
    elif slot == 3:
        if "prove" in stem.lower() or "tangent" in stem.lower():
            new_ans = build_converse_tangent_proof_answer()
    elif slot == 4:
        parsed = parse_external_tangent_givens(stem)
        if parsed:
            rs, rl, d = parsed
            c1, c2 = "G", "H"
            centres = re.search(r"\bcentres?\s+([A-Z])\s+and\s+([A-Z])\b", stem, re.I)
            if centres:
                c1, c2 = centres.group(1).upper(), centres.group(2).upper()
            new_ans = build_external_tangent_answer(rs, rl, d, c1, c2)
    elif slot == 5:
        og_m = _OG_FROM_O_RE.search(stem)
        gj_m = _GJ_RE.search(stem)
        if og_m and gj_m and outer_r is not None and pa_len is not None:
            new_ans = build_fusion_answer(
                outer_r,
                pa_len,
                float(og_m.group(1)),
                float(gj_m.group(1)),
            )

    if new_ans:
        if slot == 2:
            new_ans = fix_secant_answer_variables(stem, new_ans)
        out["correct_answer"] = new_ans
        out["answer_synced"] = True
        if slot == 1:
            out["explanation"] = "Concentric anchor; R² − r² is a perfect square."
        elif slot == 2:
            out["explanation"] = "Tangent–secant power; values match Question 1 outer radius."
        elif slot == 4:
            out["explanation"] = "Direct common external tangent."
        elif slot == 5:
            out["explanation"] = "Fusion cites Q1 radius and Q2 tangent length."

    return finalize_question_dict(out)


def sync_paper_answers(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
) -> List[Dict[str, Any]]:
    """Sync all answers to match repaired stems (answer key = question values)."""
    ordered = sorted(
        questions,
        key=lambda x: (_slot_index(x, 99), x.get("order_index", 0)),
    )
    by_slot = {_slot_index(q, i + 1): q for i, q in enumerate(ordered)}
    q1 = (by_slot.get(1) or {}).get("content") or ""
    q2 = (by_slot.get(2) or {}).get("content") or ""

    out: List[Dict[str, Any]] = []
    for i, q in enumerate(ordered):
        slot = _slot_index(q, i + 1)
        synced = sync_answer_for_slot(
            q, slot, chapter=chapter, q1_stem=q1, q2_stem=q2
        )
        out.append(synced)
    return out


def extract_value_map(text: str) -> Dict[str, float]:
    """Key measurements for cross-check (PA, PQ, radii, GH, GJ, OG)."""
    if not text:
        return {}
    m: Dict[str, float] = {}
    pa = _PA_RE.search(text)
    pq = _PQ_RE.search(text)
    gj = _GJ_RE.search(text)
    og = _OG_FROM_O_RE.search(text)
    if pa:
        m["PA"] = float(pa.group(1))
    if pq:
        m["PQ"] = float(pq.group(1))
    if gj:
        m["GJ"] = float(gj.group(1))
    if og:
        m["OG"] = float(og.group(1))
    radii = parse_concentric_radii(text)
    if radii:
        m["R_outer"] = radii[0]
        m["r_inner"] = radii[1]
    ext = parse_external_tangent_givens(text)
    if ext:
        m["r_small"] = ext[0]
        m["r_large"] = ext[1]
        m["GH_dist"] = ext[2]
    gh_centre = re.search(r"\bGH\s*=\s*(\d+(?:\.\d+)?)\s*cm", text, re.I)
    if gh_centre:
        m["GH"] = float(gh_centre.group(1))
    return m


def answer_stem_value_mismatches(
    stem: str,
    answer: str,
    *,
    keys: Optional[Tuple[str, ...]] = None,
) -> List[str]:
    """Return human-readable mismatches when answer uses different givens than stem."""
    keys = keys or ("PA", "PQ", "GJ", "OG", "R_outer", "r_inner", "GH", "r_small", "r_large", "GH_dist")
    sm = extract_value_map(stem)
    am = extract_value_map(answer)
    issues: List[str] = []
    for k in keys:
        if k in sm and k in am and abs(sm[k] - am[k]) > 0.5:
            issues.append(f"{k}: stem={_int(sm[k])} answer={_int(am[k])}")
    return issues
