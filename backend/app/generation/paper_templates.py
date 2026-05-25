"""
Paper template registry — abstract slot roles + topic-specific buckets.

Template A (chained_concentric) remains the default for Class 10 Circles hard papers.
Other templates disable or relax the dependency chain while keeping slot-role prompts.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.config import settings


class SlotRole(str, Enum):
    """Topic-agnostic slot purpose (maps to concrete buckets per chapter)."""

    ANCHOR = "anchor"
    HENCE_A = "hence_a"
    PROOF = "proof"
    INDEPENDENT = "independent"
    FUSION = "fusion"
    CASE_STUDY = "case_study"


@dataclass(frozen=True)
class TemplateSlot:
    role: SlotRole
    topic_bucket: str = ""  # circles: concentric_chord, secant_tangent_power, …
    marks_hint: int = 0


@dataclass(frozen=True)
class PaperTemplate:
    id: str
    name: str
    description: str
    subjects: Tuple[str, ...] = ("Mathematics",)
    topics: Tuple[str, ...] = ("*",)
    classes: Tuple[int, ...] = (9, 10, 11, 12)
    exam_patterns: Tuple[str, ...] = ("CBSE", "State Board", "board")
    enables_dependency_chain: bool = False
    slots: Tuple[TemplateSlot, ...] = ()

    def slot_for_index(self, index: int) -> Optional[TemplateSlot]:
        if not self.slots or index < 0:
            return None
        if index < len(self.slots):
            return self.slots[index]
        return self.slots[-1]


# ── Circles Template A (current production blueprint) ─────────────────────────

_CHAINED_CONCENTRIC_5: Tuple[TemplateSlot, ...] = (
    TemplateSlot(SlotRole.ANCHOR, "concentric_chord", 5),
    TemplateSlot(SlotRole.HENCE_A, "secant_tangent_power", 6),
    TemplateSlot(SlotRole.PROOF, "tangent_perpendicular_proof", 5),
    TemplateSlot(SlotRole.INDEPENDENT, "common_external_tangent", 5),
    TemplateSlot(SlotRole.FUSION, "fusion_hots", 7),
)

_CHAINED_CONCENTRIC_10: Tuple[TemplateSlot, ...] = _CHAINED_CONCENTRIC_5 + (
    TemplateSlot(SlotRole.INDEPENDENT, "tangent_lengths_equal", 5),
    TemplateSlot(SlotRole.INDEPENDENT, "cyclic_or_similarity", 5),
    TemplateSlot(SlotRole.INDEPENDENT, "alternate_segment_angle", 5),
    TemplateSlot(SlotRole.PROOF, "proof_based", 6),
    TemplateSlot(SlotRole.HENCE_A, "secant_tangent_power", 6),
)

# ── Template C — revision / mixed (no cross-refs) ───────────────────────────

_MIXED_INDEPENDENT_5: Tuple[TemplateSlot, ...] = (
    TemplateSlot(SlotRole.INDEPENDENT, "", 5),
    TemplateSlot(SlotRole.INDEPENDENT, "", 5),
    TemplateSlot(SlotRole.PROOF, "", 5),
    TemplateSlot(SlotRole.INDEPENDENT, "", 5),
    TemplateSlot(SlotRole.CASE_STUDY, "fusion_hots", 6),
)

# ── Template B — placeholder (similarity chain; dependency TBD) ─────────────

_CHAINED_TRIANGLE_5: Tuple[TemplateSlot, ...] = (
    TemplateSlot(SlotRole.ANCHOR, "similarity_anchor", 5),
    TemplateSlot(SlotRole.HENCE_A, "ratio_from_similarity", 6),
    TemplateSlot(SlotRole.PROOF, "pythagoras_or_converse", 5),
    TemplateSlot(SlotRole.INDEPENDENT, "area_ratio", 5),
    TemplateSlot(SlotRole.FUSION, "fusion_trig_area", 7),
)


PAPER_TEMPLATES: Dict[str, PaperTemplate] = {
    "chained_concentric": PaperTemplate(
        id="chained_concentric",
        name="Chained Concentric (Circles)",
        description=(
            "CBSE-style linked paper: Q1 anchor establishes shared figure; "
            "Q2 Hence from Q1; Q5 fusion uses Q1+Q2."
        ),
        subjects=("Mathematics",),
        topics=("circles", "Circles"),
        classes=(10,),
        exam_patterns=("CBSE", "State Board", "board"),
        enables_dependency_chain=True,
        slots=_CHAINED_CONCENTRIC_5,
    ),
    "chained_triangle": PaperTemplate(
        id="chained_triangle",
        name="Chained Triangle (Similarity)",
        description="Anchor similarity proof; Hence ratio; proof; area; fusion (stub — no dependency chain yet).",
        subjects=("Mathematics",),
        topics=("triangles", "similarity", "Triangles"),
        classes=(10,),
        exam_patterns=("CBSE", "State Board", "board"),
        enables_dependency_chain=False,
        slots=_CHAINED_TRIANGLE_5,
    ),
    "mixed_independent": PaperTemplate(
        id="mixed_independent",
        name="Mixed Independent (Revision)",
        description="Five standalone hard questions; no Question 1→2 cross-references.",
        subjects=("Mathematics", "Science"),
        topics=("*",),
        classes=(9, 10, 11, 12),
        exam_patterns=("CBSE", "State Board", "JEE", "NEET", "board", "jee_mains"),
        enables_dependency_chain=False,
        slots=_MIXED_INDEPENDENT_5,
    ),
}


def list_paper_templates() -> List[Dict[str, Any]]:
    """Serialize registry for API / UI."""
    out: List[Dict[str, Any]] = []
    for t in PAPER_TEMPLATES.values():
        out.append(
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "subjects": list(t.subjects),
                "topics": list(t.topics),
                "classes": list(t.classes),
                "exam_patterns": list(t.exam_patterns),
                "enables_dependency_chain": t.enables_dependency_chain,
                "slots": [
                    {
                        "role": s.role.value,
                        "topic_bucket": s.topic_bucket or None,
                        "marks_hint": s.marks_hint,
                    }
                    for s in t.slots
                ],
            }
        )
    return out


def get_paper_template(template_id: str) -> Optional[PaperTemplate]:
    return PAPER_TEMPLATES.get((template_id or "").strip().lower())


def _topic_matches(template: PaperTemplate, chapter: str) -> bool:
    if "*" in template.topics:
        return True
    ch = (chapter or "").strip().lower()
    return any(ch == t.lower() or t.lower() in ch for t in template.topics)


def _exam_matches(template: PaperTemplate, exam_track: str) -> bool:
    if not template.exam_patterns:
        return True
    track = (exam_track or "board").strip().lower()
    for p in template.exam_patterns:
        if p.lower() in track or track in p.lower():
            return True
    return track in ("board", "cbse")


def resolve_paper_template(
    *,
    override: Optional[str] = None,
    plan_template_id: Optional[str] = None,
    chapter: str = "generic",
    subject: str = "Mathematics",
    class_level: str = "10",
    exam_track: str = "board",
    question_count: int = 5,
    ui_difficulty: str = "medium",
    full_hard: bool = False,
) -> PaperTemplate:
    """
    Pick template: config override > semantic-plan id > DEFAULT_PAPER_TEMPLATE > auto rules.

    Auto: Circles + hard/full-hard + ≥3 questions → chained_concentric; else mixed_independent.

    plan_template_id keeps finalize/integrity aligned with the prompt compiler when
    difficulty would otherwise re-tier to chained_concentric.
    """
    for candidate in (
        override,
        plan_template_id,
        settings.DEFAULT_PAPER_TEMPLATE,
    ):
        raw = (candidate or "").strip().lower()
        if raw and raw != "auto":
            found = get_paper_template(raw)
            if found:
                return found

    ch = (chapter or "generic").strip().lower()
    ui = (ui_difficulty or "medium").lower()
    hard = ui in ("hard", "difficult") or full_hard

    if ch == "circles" and hard and question_count >= 3:
        return PAPER_TEMPLATES["chained_concentric"]

    if ch == "trigonometry" and hard and question_count >= 3:
        return PAPER_TEMPLATES["mixed_independent"]

    if ch in ("triangles", "similarity") and hard and question_count >= 3:
        return PAPER_TEMPLATES.get("chained_triangle") or PAPER_TEMPLATES["mixed_independent"]

    return PAPER_TEMPLATES["mixed_independent"]


def template_slots_for_count(template: PaperTemplate, question_count: int) -> Tuple[TemplateSlot, ...]:
    """Extend or trim slot role list to match question_count."""
    if question_count <= 0:
        return ()
    base = template.slots
    if not base:
        return tuple(
            TemplateSlot(SlotRole.INDEPENDENT, "", 5) for _ in range(question_count)
        )
    if question_count <= len(base):
        return base[:question_count]
    out = list(base)
    while len(out) < question_count:
        out.append(base[-1])
    return tuple(out)


def slot_role_directive(
    slot_index: int,
    *,
    template: PaperTemplate,
    chapter: str = "circles",
    question_count: int = 5,
) -> str:
    """One-line prompt directive: abstract role + optional topic bucket."""
    slots = template_slots_for_count(template, question_count)
    if slot_index >= len(slots):
        return ""
    spec = slots[slot_index]
    role = spec.role.value.upper()
    bucket = spec.topic_bucket
    if bucket:
        return (
            f"REQUIRED SLOT ROLE for Q{slot_index + 1}: {role} "
            f"(topic bucket: {bucket} — use this reasoning structure only)."
        )
    return (
        f"REQUIRED SLOT ROLE for Q{slot_index + 1}: {role} "
        f"(standalone — do not reference earlier questions)."
    )


def template_slot_assignments_block(
    template: PaperTemplate,
    question_count: int,
    chapter: str = "circles",
) -> str:
    """Prompt block replacing hardcoded concentric-only SLOT BUCKET lines."""
    slots = template_slots_for_count(template, question_count)
    if not slots:
        return ""
    lines = [
        f"PAPER TEMPLATE: {template.id} — {template.name}",
        f"  {template.description}",
    ]
    if template.enables_dependency_chain:
        lines.append("  Cross-question references (Hence / from Question N) are REQUIRED where the dependency graph specifies.")
    else:
        lines.append("  Cross-question references are FORBIDDEN — each question is standalone.")
    lines.append("SLOT ROLE ASSIGNMENTS (mandatory):")
    for i, spec in enumerate(slots):
        role = spec.role.value
        if spec.topic_bucket:
            lines.append(f"  Q{i + 1}: role={role} | bucket={spec.topic_bucket}")
        else:
            lines.append(f"  Q{i + 1}: role={role} | pick any hard {chapter} structure not used in prior slots")
    return "\n".join(lines)


def template_header_for_plan(template: PaperTemplate) -> str:
    chain = "enabled" if template.enables_dependency_chain else "disabled"
    return f"Paper template: {template.id} ({template.name}); dependency chain {chain}."
