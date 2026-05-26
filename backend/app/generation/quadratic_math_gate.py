"""
Hard gate for quadratic stem + model-answer math — used on every generation path.

Math failures are never bypassed by force-apply or lenient quality modes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

logger = logging.getLogger(__name__)


def math_verification_flags(question: Dict[str, Any]) -> List[str]:
    from app.core.config import settings

    if not settings.ENABLE_QUADRATIC_MATH_VERIFY:
        return []
    from app.generation.quadratic_math_verify import verify_quadratic_question_math

    return list(
        verify_quadratic_question_math(question).get("math_verification_flags") or []
    )


def should_block_quadratic_math(question: Dict[str, Any]) -> bool:
    return bool(math_verification_flags(question))


def annotate_math_verification(question: Dict[str, Any]) -> Dict[str, Any]:
    flags = math_verification_flags(question)
    question["math_verification_ok"] = not flags
    question["math_verification_flags"] = flags
    return question


def filter_quadratic_math_verified(
    questions: Sequence[Dict[str, Any]],
    *,
    drop: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Drop (or flag) questions that fail computational verification."""
    kept: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for q in questions:
        item = annotate_math_verification(dict(q))
        if item.get("math_verification_ok", True):
            kept.append(item)
        else:
            rejected.append(item)
            if not drop:
                kept.append(item)
    return (kept if drop else list(questions)), rejected


def pool_math_verification_report(
    questions: Sequence[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """Return (ok, human-readable reasons per slot)."""
    reasons: List[str] = []
    for i, q in enumerate(questions):
        flags = math_verification_flags(q)
        if flags:
            sn = q.get("slot_number") or q.get("id") or (i + 1)
            reasons.append(f"Q{sn}:{';'.join(flags[:3])}")
    return (not reasons, reasons)


def verify_parsed_questions_for_chapter(
    questions: Sequence[Dict[str, Any]],
    *,
    chapter: str,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Run math verification on parsed items; return (annotated_list, all_reasons).
    No-op when chapter is not quadratic or verify disabled.
    """
    ch = (chapter or "").strip().lower()
    if ch != "quadratic":
        return list(questions), []
    from app.core.config import settings

    if not settings.ENABLE_QUADRATIC_MATH_VERIFY:
        return list(questions), []
    annotated: List[Dict[str, Any]] = []
    reasons: List[str] = []
    for q in questions:
        item = annotate_math_verification(dict(q))
        annotated.append(item)
        if not item.get("math_verification_ok", True):
            sn = item.get("slot_number") or item.get("id") or "?"
            reasons.append(
                f"Q{sn}:{';'.join((item.get('math_verification_flags') or [])[:2])}"
            )
    return annotated, reasons


def validate_rag_answer_json(answer_text: str, *, chapter: str) -> None:
    """
    Parse rag_response ANSWER JSON and raise if any item fails math verification.
    Called when rag_response.txt is read so bad pools fail before apply-rag.
    """
    import json

    ch = (chapter or "").strip().lower()
    if ch != "quadratic":
        return
    from app.core.config import settings

    if not settings.ENABLE_QUADRATIC_MATH_VERIFY:
        return
    start = answer_text.find("[")
    end = answer_text.rfind("]") + 1
    if start == -1 or end <= start:
        return
    try:
        items = json.loads(answer_text[start:end])
    except json.JSONDecodeError:
        return
    if not isinstance(items, list):
        return
    pool: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pool.append(
            {
                "id": item.get("id"),
                "slot_number": item.get("id"),
                "question": item.get("question") or item.get("content") or "",
                "content": item.get("question") or item.get("content") or "",
                "correct_answer": item.get("correct_answer") or item.get("answer") or "",
            }
        )
    if pool:
        require_quadratic_pool_math_verified(pool)


def require_quadratic_pool_math_verified(
    questions: Sequence[Dict[str, Any]],
) -> None:
    """
    Raise ValueError if any question fails math verification.
    Used by apply-rag and final delivery guards (not bypassed by force).
    """
    from app.core.config import settings

    if not settings.ENABLE_QUADRATIC_MATH_VERIFY:
        return
    if not settings.QUADRATIC_MATH_VERIFY_BLOCK_DELIVERY:
        return
    ok, reasons = pool_math_verification_report(questions)
    if not ok:
        raise ValueError(
            "Quadratic math verification failed: " + "; ".join(reasons[:10])
        )
