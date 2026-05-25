"""
Auto-repair papers before export — Q2 chord dedup, clean concentric radii, LaTeX, figures.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.common_tangent_values import repair_external_tangent_stem
from app.generation.concentric_values import (
    RECOMMENDED_PAIRS,
    is_perfect_square_chord_pair,
    parse_concentric_radii,
)
from app.generation.fusion_q5_values import (
    outer_radius_from_paper,
    repair_fusion_q5_stem,
)
from app.generation.tangent_secant_values import repair_tangent_secant_stem
from app.generation.question_text import ensure_plain_text

_RADII_LINE_RE = re.compile(
    r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
    re.I,
)
_PART_I_BLOCK_RE = re.compile(
    r"\(\s*i\s*\)\s*.*?(?=\(\s*ii\s*\)|\bhence\b)",
    re.I | re.S,
)
_CHORD_IN_PART_RE = re.compile(
    r"\b(?:find|length)\b.*\bchord\b|\bchord\b.*\b(?:find|length|touch)",
    re.I,
)


def sanitize_question_fields(q: Dict[str, Any]) -> Dict[str, Any]:
    """LaTeX-safe stems/answers for PDF (sin^{-1}, \\sqrt, etc.)."""
    out = dict(q)
    for key in ("content", "question", "correct_answer", "explanation"):
        if isinstance(out.get(key), str) and out[key]:
            out[key] = ensure_plain_text(out[key])
    if out.get("content"):
        out["question"] = out["content"]
    return out


def strip_q2_duplicate_chord_part(stem: str) -> str:
    """Remove Q2 (i) that repeats Q1 chord-find; keep Hence / secant part."""
    if not stem:
        return stem
    low = stem.lower()
    if "question 1" not in low and "same concentric" not in low:
        return stem
    m = _PART_I_BLOCK_RE.search(stem)
    if m and _CHORD_IN_PART_RE.search(m.group(0)):
        tail = stem[m.end() :].lstrip(" .,\n")
        if not tail.lower().startswith("hence"):
            tail = "Hence, " + tail.lstrip("., ")
        head = stem[: m.start()].rstrip(" .,\n")
        if head.endswith("."):
            result = f"{head} {tail}".strip()
        else:
            result = f"{head}. {tail}".strip()
        result = re.sub(r"\(\s*ii\s*\)\s*hence\b", "Hence", result, flags=re.I)
        result = re.sub(r"\bhence\s*,\s*hence\b", "Hence", result, flags=re.I)
        return result
    # Bare duplicate chord sentence before Hence (no (i) label)
    if _CHORD_IN_PART_RE.search(stem) and "hence" in low:
        before, _, after = stem.lower().partition("hence")
        if _CHORD_IN_PART_RE.search(before) and "question 1" in before:
            idx = stem.lower().find("hence")
            return stem[idx:].strip()
    return stem


def repair_concentric_stem_radii(
    stem: str,
    *,
    outer: int = 17,
    inner: int = 8,
) -> Tuple[str, bool]:
    if not stem or "concentric" not in stem.lower():
        return stem, False
    parsed = parse_concentric_radii(stem)
    if parsed and is_perfect_square_chord_pair(parsed[0], parsed[1]):
        return stem, False
    new, n = _RADII_LINE_RE.subn(f"radii {outer} cm and {inner} cm", stem, count=1)
    return (new if n else stem), bool(n)


def repair_slot_by_number(
    q: Dict[str, Any],
    slot: int,
    *,
    chapter: str = "circles",
) -> Dict[str, Any]:
    """Slot-aware stem/content fixes."""
    out = sanitize_question_fields(q)
    stem = out.get("content") or out.get("question") or ""
    changed = False

    if chapter == "circles" and slot == 1:
        new_stem, ch = repair_concentric_stem_radii(stem)
        if ch:
            stem = new_stem
            changed = True

    if chapter == "circles" and slot == 2:
        new_stem = strip_q2_duplicate_chord_part(stem)
        if new_stem != stem:
            stem = new_stem
            changed = True
        new_stem, ch_ts = repair_tangent_secant_stem(stem)
        if ch_ts:
            stem = new_stem
            changed = True

    if chapter == "circles" and slot == 4:
        new_stem, ch_ext = repair_external_tangent_stem(stem, seed=slot)
        if ch_ext:
            stem = new_stem
            changed = True

    if changed:
        out["content"] = stem
        out["question"] = stem
        out["paper_repaired"] = True
    return sanitize_question_fields(out)


def _local_templates_enabled() -> bool:
    from app.core.config import settings

    return bool(getattr(settings, "ENABLE_LOCAL_LLM_FALLBACK", False))


def _slot_index(q: Dict[str, Any], fallback: int) -> int:
    sn = q.get("slot_number")
    if sn is not None and int(sn) >= 1:
        return int(sn)
    return fallback


def repair_duplicate_signatures(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    """Replace later slots that share a canonical signature with a local template."""
    from app.generation.canonical_question_signature import (
        annotate_canonical_signatures,
        build_canonical_signature,
    )
    from app.generation.local_llm import local_slot_question_dict

    ordered = sorted(
        questions,
        key=lambda x: (
            int(x.get("slot_number") or 0),
            x.get("order_index", 0),
        ),
    )
    from app.generation.canonical_question_signature import (
        disambiguate_duplicate_signatures,
    )

    annotate_canonical_signatures(ordered, chapter=chapter)
    disambiguate_duplicate_signatures(ordered, chapter=chapter)
    seen: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(ordered):
        q = dict(q)
        slot = int(q.get("slot_number") or (i + 1))
        sig = q.get("canonical_signature") or build_canonical_signature(
            q, chapter=chapter
        ).key()
        if sig in seen:
            if not _local_templates_enabled():
                seen[sig] = slot
                out.append(q)
                continue
            replacement = local_slot_question_dict(
                slot - 1,
                locked_chapter=chapter,
                difficulty=difficulty,
            )
            replacement["slot_number"] = slot
            replacement["order_index"] = q.get("order_index", slot - 1)
            replacement["content"] = replacement.get("question", "")
            from app.generation.question_type_resolver import resolve_slot_question_type

            replacement["question_type"] = resolve_slot_question_type(
                chapter, slot - 1, replacement.get("type", "")
            )
            replacement["type"] = replacement["question_type"]
            replacement["paper_repaired"] = True
            replacement["signature_repaired"] = True
            q = sanitize_question_fields(replacement)
            sig = build_canonical_signature(q, chapter=chapter).key()
        seen[sig] = slot
        out.append(q)
    return out


def fill_missing_paper_slots(
    questions: List[Dict[str, Any]],
    expected_count: int,
    *,
    chapter: str = "circles",
    difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    """Insert gap-fill questions for missing slots 1..N (local templates only if enabled)."""
    by_slot: Dict[int, Dict[str, Any]] = {}
    for q in questions:
        sn = int(q.get("slot_number") or 0)
        if sn >= 1:
            by_slot[sn] = q
    for slot in range(1, expected_count + 1):
        if slot not in by_slot:
            if not _local_templates_enabled():
                import logging

                logging.getLogger(__name__).error(
                    "Slot %d missing — provide %d questions in rag_response.txt "
                    "(ENABLE_LOCAL_LLM_FALLBACK is false; no template fill).",
                    slot,
                    expected_count,
                )
                continue
            from app.generation.local_llm import local_slot_question_dict

            fill = local_slot_question_dict(
                slot - 1, locked_chapter=chapter, difficulty=difficulty
            )
            fill["slot_number"] = slot
            fill["order_index"] = slot - 1
            fill["content"] = fill.get("question", "")
            from app.generation.question_type_resolver import resolve_slot_question_type

            fill["question_type"] = resolve_slot_question_type(
                chapter, slot - 1, fill.get("type", "")
            )
            fill["type"] = fill["question_type"]
            fill["paper_repaired"] = True
            fill["slot_gap_filled"] = True
            by_slot[slot] = sanitize_question_fields(fill)
    return [by_slot[s] for s in sorted(by_slot.keys()) if s <= expected_count]


def repair_duplicate_slot_stems(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
) -> List[Dict[str, Any]]:
    """
    If slots 3–4 share a stem or canonical signature (e.g. two common-tangent drills),
    replace slot 3 with the chapter converse-proof template.
    """
    if chapter != "circles" or len(questions) < 4:
        return questions

    from app.generation.canonical_question_signature import build_canonical_signature
    from app.generation.paper_integrity import _normalize_stem

    ordered = sorted(
        questions,
        key=lambda x: (_slot_index(x, 99), x.get("order_index", 0)),
    )
    by_slot: Dict[int, Dict[str, Any]] = {}
    for i, q in enumerate(ordered):
        by_slot[_slot_index(q, i + 1)] = q

    q3 = by_slot.get(3)
    q4 = by_slot.get(4)
    if not q3 or not q4:
        return questions

    s3 = _normalize_stem(q3.get("content") or q3.get("question") or "")
    s4 = _normalize_stem(q4.get("content") or q4.get("question") or "")
    sig3 = build_canonical_signature(q3).key()
    sig4 = build_canonical_signature(q4).key()
    needs_fix = (s3 and s3 == s4) or (
        sig3 == sig4 and "common_external_tangent" in sig3
    )
    if not needs_fix:
        return questions

    from app.generation.local_llm import _CIRCLES_HARD_FIGURE_SLOTS

    tmpl = _CIRCLES_HARD_FIGURE_SLOTS[2]
    replacement = dict(q3)
    replacement["content"] = tmpl["stem"]
    replacement["question"] = tmpl["stem"]
    replacement["correct_answer"] = tmpl["answer"]
    replacement["archetype_id"] = tmpl.get("archetype_id", "chord_tangent")
    replacement["theorem_tags"] = [
        "tangent_radius_perpendicular",
        "converse_tangent",
    ]
    replacement["paper_repaired"] = True
    replacement["slot_role_repaired"] = "converse_proof_slot3"
    by_slot[3] = sanitize_question_fields(replacement)

    out: List[Dict[str, Any]] = []
    for i, q in enumerate(ordered):
        slot = _slot_index(q, i + 1)
        out.append(by_slot.get(slot, q))
    return out


def repair_mixed_independent_slot_roles(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    paper_template_id: str = "",
    difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    """Replace slots that violate mixed_independent roles (no Q1 refs in slots 1–4)."""
    from app.generation.paper_integrity import (
        _is_mixed_independent_template,
        question_matches_slot_role,
    )
    from app.generation.local_llm import local_slot_question_dict

    if chapter != "circles" or not _is_mixed_independent_template(paper_template_id):
        return questions

    ordered = sorted(
        questions,
        key=lambda x: (_slot_index(x, 99), x.get("order_index", 0)),
    )
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(ordered):
        slot = _slot_index(q, i + 1)
        if question_matches_slot_role(
            q, slot, chapter=chapter, paper_template_id=paper_template_id
        ):
            out.append(q)
            continue
        if not _local_templates_enabled():
            out.append(q)
            continue
        from app.generation.local_llm import local_slot_question_dict

        replacement = local_slot_question_dict(
            slot - 1,
            locked_chapter=chapter,
            difficulty=difficulty,
            paper_template_id=paper_template_id,
        )
        replacement["slot_number"] = slot
        replacement["order_index"] = q.get("order_index", slot - 1)
        replacement["content"] = replacement.get("question", "")
        from app.generation.question_type_resolver import resolve_slot_question_type

        replacement["question_type"] = resolve_slot_question_type(
            chapter, slot - 1, replacement.get("type", "")
        )
        replacement["type"] = replacement["question_type"]
        replacement["paper_repaired"] = True
        replacement["slot_role_repaired"] = f"mixed_independent_slot{slot}"
        out.append(sanitize_question_fields(replacement))
    return out


def repair_fusion_slot5_in_paper(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
) -> List[Dict[str, Any]]:
    """Slot 5 fusion — clean OG/GJ given outer R from Q1."""
    if chapter != "circles" or not questions:
        return questions
    ordered = sorted(
        questions,
        key=lambda x: (
            int(x.get("slot_number") or 0),
            x.get("order_index", 0),
        ),
    )
    by_slot = {int(q.get("slot_number") or 0): q for q in ordered}
    q1 = by_slot.get(1) or ordered[0]
    q5 = by_slot.get(5) or (ordered[4] if len(ordered) >= 5 else None)
    if not q5:
        return questions
    outer_r = outer_radius_from_paper(q1.get("content") or q1.get("question") or "")
    if not outer_r:
        return questions
    stem = q5.get("content") or q5.get("question") or ""
    new_stem, changed = repair_fusion_q5_stem(stem, outer_r, seed=0)
    if not changed:
        return questions
    q5 = dict(q5)
    q5["content"] = new_stem
    q5["question"] = new_stem
    q5["paper_repaired"] = True
    q5["fusion_values_repaired"] = True
    q5 = sanitize_question_fields(q5)
    out: List[Dict[str, Any]] = []
    for q in ordered:
        slot = int(q.get("slot_number") or 0)
        out.append(q5 if slot == 5 else q)
    return out


def repair_paper_questions(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    re_enrich_figures: bool = True,
    paper_template_id: str = "",
) -> List[Dict[str, Any]]:
    """Apply all automatic repairs in slot order."""
    if not paper_template_id:
        try:
            from app.generation.topic_isolation import get_current_topic_state

            paper_template_id = (get_current_topic_state() or {}).get(
                "paper_template_id", ""
            ) or ""
        except Exception:
            paper_template_id = ""
    questions = repair_mixed_independent_slot_roles(
        questions,
        chapter=chapter,
        paper_template_id=paper_template_id,
    )
    questions = repair_duplicate_slot_stems(questions, chapter=chapter)
    questions = repair_fusion_slot5_in_paper(questions, chapter=chapter)
    questions = repair_duplicate_signatures(questions, chapter=chapter)
    ordered = sorted(
        questions,
        key=lambda x: (
            int(x.get("slot_number") or 0),
            x.get("order_index", 0),
        ),
    )
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(ordered):
        slot = int(q.get("slot_number") or (i + 1))
        fixed = repair_slot_by_number(q, slot, chapter=chapter)
        if re_enrich_figures and fixed.get("question_type") == "FigureBased":
            stem = fixed.get("content") or ""
            from app.generation.figure_spec_builder import enrich_figure_spec
            from app.generation.figure_label_validator import needs_figure_rebuild

            old_spec = dict(fixed.get("figure_spec") or {})
            if needs_figure_rebuild(stem, old_spec):
                spec = enrich_figure_spec(stem, None)
                fixed["figure_url"] = None
            else:
                spec = enrich_figure_spec(stem, old_spec)
            fixed["figure_spec"] = spec
            fixed["figure_type"] = fixed.get("figure_type") or spec.get(
                "type", "labeled_diagram"
            )
        out.append(sanitize_question_fields(fixed))
    from app.generation.answer_sync import sync_paper_answers

    return sync_paper_answers(out, chapter=chapter)


def pick_default_concentric_pair(seed: int = 0) -> Tuple[int, int, int]:
    """Return (R, r, chord) from recommended board-friendly pairs."""
    idx = abs(seed) % len(RECOMMENDED_PAIRS)
    return RECOMMENDED_PAIRS[idx]
