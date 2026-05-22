"""
Human curation loop — strip meta language, compress stems, controlled imperfection.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple, Optional

from app.generation.textbook_constants import BANNED_META_PHRASES, MIN_STEM_WORDS
from app.generation.idiomatic_geometry_patterns import apply_idiomatic_fix
from app.generation.question_completeness import _is_conceptual_one_liner, ensure_minimum_context
from app.generation.geometry_graph_validator import validate_geometry_graph


_STRIP_PATTERNS = [
    r"\s*[.,]?\s*show your working\.?",
    r"\s*[.,]?\s*show all working\.?",
    r"\s*[.,]?\s*justify briefly\.?",
    r"\s*[.,]?\s*use the diagram[^.]*\.?",
    r"\s*[.,]?\s*use the figure[^.]*\.?",
    r"\s*students often[^.]*\.?",
    r"\s*student often[^.]*\.?",
    r"\s*identify the right triangle formed[^.]*\.?",
    r"\s*radii are drawn to the points of contact in the diagram\.?",
    r"\s*touches the circle only at \w+\s*,?",
    r"\s*the segment \w+ lies along the tangent[^.]*\.?",
    r"\s*treat \w+ as the segment[^.]*\.?",
]

# Light human redundancy (not banned) — applied only when imperfect_compression slot
_HUMAN_TOUCHES = [
    ("Find ", "Find the length of "),
    ("centre O.", "centre O of the circle."),
    ("tangents PA and PB.", "tangents PA and PB to the circle."),
]


def compress_stem(text: str, *, allow_imperfection: bool = False) -> str:
    """Remove meta / over-spec; optionally keep slight human redundancy."""
    if not text:
        return text
    out = text.strip()
    for pat in _STRIP_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(
        r"^in the adjoining figure,\s*a circle has centre o and\s*",
        "O is the centre of a circle. ",
        out,
        flags=re.IGNORECASE,
    )
    if allow_imperfection and len(out.split()) < 22:
        for src, repl in _HUMAN_TOUCHES:
            if src in out and repl not in out:
                out = out.replace(src, repl, 1)
                break
    out = out.strip() or text.strip()
    fixed, _ = apply_idiomatic_fix(out)
    out = fixed
    if len(out.split()) < MIN_STEM_WORDS.get("default", 12) and not _is_conceptual_one_liner(out):
        return text.strip()
    return out


def compress_textbook_proof_answer(text: str) -> str:
    """RD Sharma style: brief congruence proof, not tutoring narration."""
    if not text or len(text) < 120:
        return text
    low = text.lower()
    if "prove" not in low and "step 1" not in low:
        return text
    if "rhs" in low or "congruent" in low or "bisects" in low:
        lines = []
        if re.search(r"pa\s*=\s*pb|equal tangents", low):
            lines.append("PA = PB (tangents from P).")
        if "oa = ob" in low.replace(" ", "") or "oa = ob" in low:
            lines.append("OA = OB and OP is common.")
        if "rhs" in low:
            lines.append("Triangles OAP and OBP are congruent (RHS).")
        if "angle opa" in low or "opa = opb" in low or "bisects" in low:
            lines.append("Hence angle OPA = angle OPB.")
            lines.append("Therefore OP bisects angle APB.")
        if lines:
            return " ".join(lines)
    return text


def apply_sparse_hard_trim(text: str) -> str:
    """Sparse hard items: strip to minimal prove/find stem if still verbose."""
    if not text or len(text.split()) <= 18:
        return text
    m = re.search(r"\b(prove that|show that|find)\b.+", text, re.I)
    if m:
        trimmed = m.group(0).strip().rstrip(".") + "."
        geo = validate_geometry_graph(trimmed)
        if "prove_equality_missing_tangent_setup" in (geo.get("geometry_flags") or []):
            return text
        return trimmed
    return text


def curate_question(
    q: Dict[str, Any],
    slot_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    content = q.get("content") or ""
    meta = slot_meta or {}
    allow_imperfect = meta.get("imperfect_compression", False)
    compressed = compress_stem(content, allow_imperfection=allow_imperfect)
    if meta.get("sparse_hard") and len(compressed.split()) > 22:
        compressed = apply_sparse_hard_trim(compressed)
    fixed, idiom_changed = apply_idiomatic_fix(compressed)
    compressed = fixed
    if idiom_changed:
        q["idiom_fixed"] = True
    if compressed != content:
        q["content_original"] = content
        q["content"] = compressed
        q["curated"] = True
    if allow_imperfect:
        q["human_imperfection"] = True
    if meta.get("sparse_hard"):
        q["sparse_hard"] = True
    q = ensure_minimum_context(q)
    if meta.get("exercise_memory_reuse"):
        q["exercise_memory_reuse"] = True
    if meta.get("exercise_memory_teach"):
        q["exercise_memory_teach"] = True
    ans = q.get("correct_answer")
    if isinstance(ans, str) and meta.get("sparse_hard"):
        brief = compress_textbook_proof_answer(ans)
        if brief != ans:
            q["correct_answer"] = brief
            q["answer_curated"] = True
    return q


def curate_batch(
    questions: List[Dict[str, Any]],
    slot_metadata: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    out = []
    for i, q in enumerate(questions):
        meta = None
        if slot_metadata and i < len(slot_metadata):
            meta = slot_metadata[i]
        out.append(curate_question(q, meta))
    return out


def diversity_ok(questions: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if len(questions) < 3:
        return True, ""
    ui = (questions[0].get("ui_difficulty") or "hard") if questions else "hard"
    from app.generation.reasoning_signature import reasoning_diversity_ok

    r_ok, r_reason = reasoning_diversity_ok(questions, ui_difficulty=ui)
    if not r_ok:
        return False, r_reason
    lengths = [len((q.get("content") or "").split()) for q in questions]
    if max(lengths) - min(lengths) < 8:
        return False, "stems_too_uniform_length"
    marks = [float(q.get("marks") or 1) for q in questions]
    if len(set(marks)) < 2 and len(questions) >= 5:
        return False, "marks_too_uniform"
    sparse = sum(1 for q in questions if q.get("sparse_hard"))
    if len(questions) >= 5 and sparse == 0:
        return False, "missing_sparse_hard"
    return True, ""
