"""
RAG slot hints — build retrieval / file-agent guidance from abstract slot roles.
"""
from __future__ import annotations

from typing import Optional

from app.generation.paper_templates import PaperTemplate, SlotRole, TemplateSlot, get_paper_template


def build_rag_slot_query(
    slot_role: str,
    *,
    topic: str = "Circles",
    difficulty: str = "hard",
    exam_pattern: str = "CBSE",
    topic_bucket: str = "",
    chapter: str = "circles",
) -> str:
    """
  Build a natural-language RAG hint from an abstract slot role (not a fixed archetype id).
  """
    role = (slot_role or "").strip().lower()
    diff = (difficulty or "hard").strip()
    exam = (exam_pattern or "CBSE").strip()
    ch = (topic or chapter or "chapter").strip()

    prompts = {
        SlotRole.ANCHOR.value: (
            f"Find a {diff} {ch} question that establishes a shared figure or numeric setup "
            f"(radii, roots, triangle data) usable in later questions. Prefer a standard textbook example."
        ),
        SlotRole.HENCE_A.value: (
            f"Find a {diff} {ch} question that naturally follows an anchor setup using "
            f"'Hence' or 'Therefore' — secant–tangent, ratio, or derived length on the same figure."
        ),
        SlotRole.PROOF.value: (
            f"Find a standard theorem proof or converse in {ch} suitable for {exam} Class level — "
            f"clear givens, no numeric fusion."
        ),
        SlotRole.INDEPENDENT.value: (
            f"Find a {diff} standalone {ch} question testing a different sub-concept; "
            f"no cross-reference to other questions."
        ),
        SlotRole.FUSION.value: (
            f"Find a HOTS / analytical {ch} question combining 2+ concepts with multi-step reasoning "
            f"for {exam}."
        ),
        SlotRole.CASE_STUDY.value: (
            f"Find a case-study or application-style {ch} problem ({diff}) with real-world context "
            f"or multi-part (i)/(ii)."
        ),
    }
    base = prompts.get(
        role,
        f"Find a {diff} question in {ch} aligned with {exam} syllabus.",
    )
    if topic_bucket:
        base += f" Reasoning bucket hint: {topic_bucket}."
    return base


def build_rag_slot_query_from_spec(
    spec: TemplateSlot,
    *,
    topic: str = "Circles",
    difficulty: str = "hard",
    exam_pattern: str = "CBSE",
    chapter: str = "circles",
) -> str:
    return build_rag_slot_query(
        spec.role.value,
        topic=topic,
        difficulty=difficulty,
        exam_pattern=exam_pattern,
        topic_bucket=spec.topic_bucket,
        chapter=chapter,
    )


def build_paper_rag_slot_queries(
    template_id: str,
    *,
    topic: str = "Circles",
    difficulty: str = "hard",
    exam_pattern: str = "CBSE",
    question_count: int = 5,
    chapter: str = "circles",
) -> list[str]:
    """One RAG hint per slot for file-agent / per-slot retrieval."""
    from app.generation.paper_templates import template_slots_for_count

    tmpl = get_paper_template(template_id)
    if not tmpl:
        return []
    slots = template_slots_for_count(tmpl, question_count)
    return [
        build_rag_slot_query_from_spec(
            s,
            topic=topic,
            difficulty=difficulty,
            exam_pattern=exam_pattern,
            chapter=chapter,
        )
        for s in slots
    ]
