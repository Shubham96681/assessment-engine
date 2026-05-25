"""
Generation oversample — request a larger pool, validate, then deliver the best N.

When the user selects N questions (e.g. 10), the pipeline may request pool = N * multiplier
(e.g. 20), run the usual quality gates on every item, and keep the top N by combined score.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.config import settings


def is_oversample_enabled() -> bool:
    return bool(getattr(settings, "GENERATION_OVERSAMPLE_ENABLED", True))


def oversample_multiplier() -> float:
    return max(1.0, float(getattr(settings, "GENERATION_OVERSAMPLE_MULTIPLIER", 2.0) or 2.0))


def pool_question_count(delivery_count: int) -> int:
    """How many questions to generate / accept in rag_response before selection."""
    n = max(1, int(delivery_count))
    if not is_oversample_enabled():
        return n
    pool = int(math.ceil(n * oversample_multiplier()))
    cap = max(n, int(getattr(settings, "MAX_QUESTIONS_PER_GENERATION", 100) or 100))
    return min(cap, max(n, pool))


def is_oversample_active(delivery_count: int) -> bool:
    return pool_question_count(delivery_count) > max(1, int(delivery_count))


def oversample_prompt_note(delivery_count: int) -> str:
    """Extra line for RAG / file-agent prompts when pool > delivery."""
    delivery = max(1, int(delivery_count))
    pool = pool_question_count(delivery)
    if pool <= delivery:
        return ""
    return (
        f"\nOVERSAMPLE: Write exactly {pool} questions with ids \"1\" through \"{pool}\". "
        f"After server-side validation, the best {delivery} are kept for the final paper.\n"
    )


def _quality_sort_key(q: Dict[str, Any]) -> float:
    try:
        return float(
            q.get("combined_score")
            or q.get("quality_score")
            or q.get("topic_alignment_score")
            or 0.0
        )
    except (TypeError, ValueError):
        return 0.0


def select_best_questions(
    questions: List[Dict[str, Any]],
    delivery_count: int,
    *,
    quality_gate: Optional[Callable[..., bool]] = None,
    ui_difficulty: str = "medium",
    slot_meta: Optional[List[Dict[str, Any]]] = None,
    chapter: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Filter rejected items (when quality_gate provided), rank by score, keep top N,
    renumber slots 1..N.
    """
    delivery = max(1, int(delivery_count))
    candidates = [
        dict(q)
        for q in questions
        if (q.get("content") or q.get("question") or "").strip()
    ]
    rejected: List[Dict[str, Any]] = []
    accepted: List[Dict[str, Any]] = []
    for i, q in enumerate(candidates):
        meta = slot_meta[i] if slot_meta and i < len(slot_meta) else None
        if quality_gate and quality_gate(
            q, ui_difficulty=ui_difficulty, slot_meta=meta
        ):
            q["oversample_rejected"] = True
            rejected.append(q)
        else:
            accepted.append(q)

    accepted.sort(key=_quality_sort_key, reverse=True)
    if len(accepted) >= delivery:
        selected = accepted[:delivery]
    else:
        rejected.sort(key=_quality_sort_key, reverse=True)
        selected = (accepted + rejected)[:delivery]

    for i, q in enumerate(selected):
        q["slot_number"] = i + 1
        q["order_index"] = i
        if q.get("id") is not None:
            q["id"] = str(i + 1)
        if chapter:
            q["locked_chapter"] = chapter

    return selected, {
        "delivery_count": delivery,
        "pool_received": len(questions),
        "candidates_nonempty": len(candidates),
        "accepted_after_gate": len(accepted),
        "rejected_by_gate": len(rejected),
        "delivered": len(selected),
    }


def _stem_key(q: Dict[str, Any]) -> str:
    return ((q.get("content") or q.get("question") or "").strip().lower())[:240]


def _trial_paper_ok(
    trial: List[Dict[str, Any]],
    spec: Any,
) -> bool:
    from app.generation.chapter_paper_quality import (
        annotate_chapter_paper_quality,
        validate_stem_pattern_caps,
    )

    if validate_stem_pattern_caps(trial, spec):
        return False
    annotate_chapter_paper_quality(trial, chapter=spec.chapter_key)
    for q in trial:
        for f in q.get("chapter_quality_flags") or []:
            if f.startswith("skill_family_cap:") or f.startswith("marks_inflated"):
                return False
    return True


def select_best_for_chapter(
    questions: List[Dict[str, Any]],
    delivery_count: int,
    *,
    chapter: str,
    quality_gate: Optional[Callable[..., bool]] = None,
    ui_difficulty: str = "medium",
    slot_meta: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Pick delivery_count items matching the chapter slot plan and quality caps
    (skill families, stem-pattern limits), not merely the highest scores.
    """
    from app.generation.chapter_paper_quality import (
        get_chapter_quality_spec,
        normalize_chapter_paper_marks,
        planned_archetype_ids,
        _resolve_archetype_id,
    )

    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return select_best_questions(
            questions,
            delivery_count,
            quality_gate=quality_gate,
            ui_difficulty=ui_difficulty,
            slot_meta=slot_meta,
            chapter=chapter,
        )

    delivery = max(1, int(delivery_count))
    plan = planned_archetype_ids(chapter, delivery, ui_difficulty=ui_difficulty)
    candidates = [
        dict(q)
        for q in questions
        if (q.get("content") or q.get("question") or "").strip()
    ]
    if quality_gate:
        candidates = [
            q
            for q in candidates
            if not quality_gate(
                q, ui_difficulty=ui_difficulty, slot_meta=None
            )
        ]
    candidates.sort(key=_quality_sort_key, reverse=True)

    by_arch: Dict[str, List[Dict[str, Any]]] = {}
    for q in candidates:
        aid = (q.get("archetype_id") or "").strip() or _resolve_archetype_id(q, spec)
        q["archetype_id"] = aid
        by_arch.setdefault(aid, []).append(q)

    selected: List[Dict[str, Any]] = []
    used_stems: set[str] = set()

    def _try_pick(pool: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for q in pool:
            sk = _stem_key(q)
            if sk in used_stems:
                continue
            trial = selected + [q]
            if _trial_paper_ok(trial, spec):
                return q
        return None

    for target_aid in plan:
        if len(selected) >= delivery:
            break
        picked = _try_pick(by_arch.get(target_aid, []))
        if not picked:
            for q in candidates:
                sk = _stem_key(q)
                if sk in used_stems:
                    continue
                trial = selected + [q]
                if _trial_paper_ok(trial, spec):
                    picked = q
                    break
        if picked:
            selected.append(picked)
            used_stems.add(_stem_key(picked))

    for q in candidates:
        if len(selected) >= delivery:
            break
        sk = _stem_key(q)
        if sk in used_stems:
            continue
        trial = selected + [q]
        if _trial_paper_ok(trial, spec):
            selected.append(q)
            used_stems.add(sk)

    for i, q in enumerate(selected[:delivery]):
        q["slot_number"] = i + 1
        q["order_index"] = i
        if q.get("id") is not None:
            q["id"] = str(i + 1)
        q["locked_chapter"] = chapter

    selected = normalize_chapter_paper_marks(selected[:delivery], chapter=chapter)

    return selected, {
        "delivery_count": delivery,
        "pool_received": len(questions),
        "delivered": len(selected),
        "selection": "chapter_plan",
        "plan_archetypes": plan[:delivery],
    }


async def score_and_select_best(
    questions: List[Dict[str, Any]],
    delivery_count: int,
    *,
    quality_scorer: Any,
    ui_difficulty: str = "medium",
    slot_bands: Optional[List[str]] = None,
    slot_metadata: Optional[List[Dict[str, Any]]] = None,
    chapter: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Score batch then select delivery_count questions respecting chapter caps."""
    bands = slot_bands or []
    meta = slot_metadata or []
    scored = await quality_scorer.score_batch(
        questions,
        slot_bands=bands,
        ui_difficulty=ui_difficulty,
        slot_metadata=meta,
    )
    gate = quality_scorer.should_reject
    ch = (chapter or "").strip().lower()
    if ch:
        return select_best_for_chapter(
            scored,
            delivery_count,
            chapter=ch,
            quality_gate=gate,
            ui_difficulty=ui_difficulty,
            slot_meta=meta,
        )
    return select_best_questions(
        scored,
        delivery_count,
        quality_gate=gate,
        ui_difficulty=ui_difficulty,
        slot_meta=meta,
        chapter=chapter,
    )
