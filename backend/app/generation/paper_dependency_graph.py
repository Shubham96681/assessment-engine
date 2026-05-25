"""
Paper-level theorem dependency graph — chained reasoning across questions.

Turns independent hard slots into a flow: earlier slots derive intermediates
that later slots must consume (stems reference prior questions; answers cite them).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ── Theorem DAG (Circles) — backward walk for chained papers ─────────────────
# Tangent_perpendicular_radius → Tangent_chord_angle → Power_of_a_point → Fusion
CIRCLES_THEOREM_DAG: Dict[str, Tuple[str, ...]] = {
    "tangent_perpendicular_radius": (),
    "tangent_chord_angle": ("tangent_perpendicular_radius",),
    "equal_tangents": ("tangent_perpendicular_radius",),
    "secant_tangent_power": ("tangent_perpendicular_radius",),
    "concentric_chord": ("tangent_perpendicular_radius",),
    "common_external_tangent": ("tangent_perpendicular_radius",),
    "fusion_hots": ("concentric_chord", "secant_tangent_power"),
}

# ── Circles: 5-slot hard / full-hard dependency blueprint ─────────────────────

CIRCLES_DEPENDENCY_CHAIN_5: List[Dict[str, Any]] = [
    {
        "slot": 1,
        "depends_on": [],
        "derives": ["outer_radius_R", "inner_radius_r", "chord_length"],
        "preferred_archetypes": ("concentric", "chord_tangent"),
        "stem_directive": (
            "Establish concentric circles with centre O and radii R > r. "
            "Find the chord of the larger circle touching the smaller (name chord and contact point)."
        ),
        "answer_directive": "Model answer ends with chord length as a clear numeric result (Hence … cm).",
    },
    {
        "slot": 2,
        "depends_on": [1],
        "consumes": {1: ["outer_radius_R", "inner_radius_r", "chord_length"]},
        "preferred_archetypes": ("hots_mixed", "secant_tangent"),
        "stem_directive": (
            "MUST open with reference to Question 1 only (do NOT also restate 'centre O, radii … cm' — one reference line). "
            "Do NOT repeat Q1 chord-find — no (i) chord part. Start directly with Hence tangent–secant on the outer circle: "
            "give tangent length and nearer secant segment only; find the remaining secant part and verify power of a point."
        ),
        "required_parts": ("Hence",),
        "answer_directive": (
            "Step 1 must cite Question 1 (outer radius from prior chord work). Opens with Hence — not a repeat chord find."
        ),
        "ban_scaffolded_chord": True,
    },
    {
        "slot": 3,
        "depends_on": [],
        "derives": ["perpendicular_radius_proof"],
        "preferred_archetypes": ("chord_tangent", "direct_theorem"),
        "stem_directive": (
            "Converse tangent proof: line through S on circle meets circle only at S; given OS ⟂ line at S — "
            "prove line is tangent at S (Theorem 10.1 converse). Independent of Q1–Q2 numerics."
        ),
    },
    {
        "slot": 4,
        "depends_on": [],
        "derives": ["external_tangent_length"],
        "preferred_archetypes": ("common_tangent", "length_find"),
        "stem_directive": "Two separate circles — direct common external tangent length (independent).",
    },
    {
        "slot": 5,
        "depends_on": [1, 2],
        "consumes": {1: ["outer_radius_R"], 2: ["secant_product", "tangent_length_PA"]},
        "preferred_archetypes": ("hidden_theorem", "secant_tangent"),
        "required_parts": ("(i)", "(ii)"),
        "stem_directive": (
            "HOTS fusion: MUST reference Question 1 outer radius and Question 2 tangent point. "
            "(i) Using OR from Q1, find OQ from Q2 data (OR ⟂ tangent, Pythagoras) — do NOT invent unrelated OF/tangent givens. "
            "(ii) Hence, for point F with OF = d cm (choose d so tangent length is consistent: d² = R² + t²), "
            "find tangent length FT, then secant with FG given — verify t² = FG × FH. NEVER state a tangent length that contradicts R from Q1."
        ),
        "answer_directive": "Cite Q1/Q2; (i) OQ must match √(R²+t²); (ii) tangent from F must equal √(OF²−R²), not an arbitrary cm value.",
    },
]

CIRCLES_DEPENDENCY_CHAIN_3: List[Dict[str, Any]] = [
    {
        "slot": 1,
        "depends_on": [],
        "derives": ["chord_length", "outer_radius_R", "inner_radius_r"],
        "preferred_archetypes": ("concentric",),
        "stem_directive": "Concentric circles — find chord touching inner circle.",
    },
    {
        "slot": 2,
        "depends_on": [1],
        "consumes": {1: ["outer_radius_R", "inner_radius_r"]},
        "preferred_archetypes": ("secant_tangent", "hots_mixed"),
        "stem_directive": "Same circles as Question 1; Hence-only tangent–secant (do NOT repeat chord find).",
        "ban_scaffolded_chord": True,
    },
    {
        "slot": 3,
        "depends_on": [1, 2],
        "consumes": {1: ["outer_radius_R"], 2: ["tangent_length"]},
        "preferred_archetypes": ("hidden_theorem",),
        "stem_directive": "Hence-style reuse of Q1–Q2 configuration — one fusion find.",
    },
]

_REF_Q_RE = re.compile(
    r"\b(?:question|q\.?)\s*(\d+)\b|"
    r"\b(?:from|in|for|using)\s+(?:the\s+)?(?:same\s+)?(?:concentric\s+)?(?:circles?\s+)?(?:as\s+)?(?:in\s+)?question\s*(\d+)\b|"
    r"\bconfiguration\s+of\s+question\s*(\d+)\b|"
    r"\babove\s+concentric\b",
    re.I,
)
_PART_I_RE = re.compile(r"\(i\)", re.I)
_PART_II_RE = re.compile(r"\(ii\)|\bhence\b", re.I)
_SCAFFOLD_CHORD_RE = re.compile(
    r"\bchord\b.*(?:\d+\s*√|\d+\s*\\sqrt|√\s*\{|sqrt\s*\(|length\s+2\s*√)",
    re.I,
)


@dataclass
class SlotDependency:
    slot: int
    depends_on_slots: List[int] = field(default_factory=list)
    derives: List[str] = field(default_factory=list)
    consumes: Dict[int, List[str]] = field(default_factory=dict)
    preferred_archetypes: Tuple[str, ...] = ()
    stem_directive: str = ""
    answer_directive: str = ""
    required_parts: Tuple[str, ...] = ()
    ban_scaffolded_chord: bool = False
    must_reference_questions: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.depends_on_slots and not self.must_reference_questions:
            self.must_reference_questions = list(self.depends_on_slots)


@dataclass
class PaperDependencyPlan:
    chapter: str
    enabled: bool
    slots: List[SlotDependency] = field(default_factory=list)
    shared_labels: Dict[str, str] = field(default_factory=dict)
    paper_template_id: str = ""

    def slot_dep(self, slot_num: int) -> Optional[SlotDependency]:
        for s in self.slots:
            if s.slot == slot_num:
                return s
        return None


def _chain_for_chapter(
    chapter: str,
    question_count: int,
    *,
    full_hard: bool,
    ui_difficulty: str,
    paper_template_id: str = "",
) -> List[Dict[str, Any]]:
    from app.generation.paper_templates import get_paper_template

    ch = (chapter or "generic").strip().lower()
    ui = (ui_difficulty or "medium").lower()
    tmpl_id = (paper_template_id or "chained_concentric").strip().lower()
    tmpl = get_paper_template(tmpl_id)
    if tmpl and not tmpl.enables_dependency_chain:
        return []
    if ch != "circles" or ui not in ("hard", "difficult"):
        return []
    if tmpl_id not in ("", "chained_concentric", "auto"):
        return []
    if question_count >= 5:
        return list(CIRCLES_DEPENDENCY_CHAIN_5[:question_count])
    if question_count >= 3:
        return list(CIRCLES_DEPENDENCY_CHAIN_3[:question_count])
    return []


def build_paper_dependency_plan(
    *,
    chapter: str,
    question_count: int,
    slots: Sequence[Any],
    ui_difficulty: str = "medium",
    full_hard: bool = False,
    paper_template_id: str = "",
) -> PaperDependencyPlan:
    """Build slot-level dependency specs for the whole paper."""
    ch = (chapter or "generic").strip().lower()
    ui = (ui_difficulty or "medium").lower()
    chain = _chain_for_chapter(
        ch,
        question_count,
        full_hard=full_hard,
        ui_difficulty=ui,
        paper_template_id=paper_template_id,
    )
    if not chain:
        return PaperDependencyPlan(chapter=ch, enabled=False)

    dep_slots: List[SlotDependency] = []
    for spec in chain:
        dep_slots.append(
            SlotDependency(
                slot=int(spec["slot"]),
                depends_on_slots=list(spec.get("depends_on") or []),
                derives=list(spec.get("derives") or []),
                consumes={int(k): list(v) for k, v in (spec.get("consumes") or {}).items()},
                preferred_archetypes=tuple(spec.get("preferred_archetypes") or ()),
                stem_directive=str(spec.get("stem_directive") or ""),
                answer_directive=str(spec.get("answer_directive") or ""),
                required_parts=tuple(spec.get("required_parts") or ()),
                ban_scaffolded_chord=bool(spec.get("ban_scaffolded_chord")),
            )
        )

    return PaperDependencyPlan(
        chapter=ch,
        enabled=True,
        slots=dep_slots,
        shared_labels={"centre": "O"},
        paper_template_id=(paper_template_id or "chained_concentric").strip().lower(),
    )


def align_archetypes_to_dependency(
    archetypes: List[Dict[str, Any]],
    dep_plan: PaperDependencyPlan,
) -> List[Dict[str, Any]]:
    """Nudge archetype picks so slots match dependency preferred_archetypes."""
    if not dep_plan.enabled or not archetypes:
        return archetypes
    from app.generation.archetype_registry import normalize_archetype_id

    out = [dict(a) for a in archetypes]
    for dep in dep_plan.slots:
        idx = dep.slot - 1
        if idx < 0 or idx >= len(out) or not dep.preferred_archetypes:
            continue
        pref = dep.preferred_archetypes[0]
        cur = normalize_archetype_id(out[idx].get("id", ""), dep_plan.chapter)
        if cur not in dep.preferred_archetypes:
            for aid in dep.preferred_archetypes:
                if aid in {normalize_archetype_id(a.get("id", ""), dep_plan.chapter) for a in out}:
                    continue
                out[idx] = {**out[idx], "id": aid, "theorem_id": aid}
                break
    return out


def dependency_prompt_section(dep_plan: PaperDependencyPlan) -> str:
    """Inject into generation prompt — mandatory cross-question reasoning flow."""
    if not dep_plan.enabled:
        return ""
    lines = [
        "PAPER DEPENDENCY GRAPH (mandatory — interconnected reasoning, NOT independent drills):",
        "- Later questions MUST logically depend on earlier deductions (same labels, same radii, Hence chains).",
        "- Do NOT give derived numeric results in a stem when an earlier question asks the student to derive them.",
        "- Model answers for dependent slots MUST cite prior questions (e.g. 'From Question 1, …').",
        "",
        "Slot chain:",
    ]
    for dep in dep_plan.slots:
        refs = ""
        if dep.depends_on_slots:
            refs = f" ← depends on Q{'+Q'.join(str(s) for s in dep.depends_on_slots)}"
        parts = ""
        if dep.required_parts:
            parts = f" | parts: {' '.join(dep.required_parts)}"
        lines.append(f"  Q{dep.slot}{refs}{parts}")
        if dep.stem_directive:
            lines.append(f"    Stem: {dep.stem_directive}")
        if dep.derives:
            lines.append(f"    Derives: {', '.join(dep.derives)}")
        if dep.answer_directive:
            lines.append(f"    Answer: {dep.answer_directive}")
        if dep.ban_scaffolded_chord:
            lines.append("    BAN: numeric chord length / 2√… in stem before (ii).")
    lines.extend(
        [
            "",
            "Q2-type pattern (when Q2 depends on Q1): reference Question 1 only; Hence-only tangent–secant — do NOT repeat chord find as (i).",
            "Q5-type pattern: fuse Q1 configuration with Q2-style secant/tangent on same paper narrative.",
        ]
    )
    return "\n".join(lines)


def _stem_references_question(stem: str, qnum: int) -> bool:
    for m in _REF_Q_RE.finditer(stem or ""):
        g = next((x for x in m.groups() if x), None)
        if g and int(g) == qnum:
            return True
    if qnum == 1 and re.search(
        r"\bsame\s+concentric\b|\bconcentric\s+circles\s+as\b|\bquestion\s+1\b",
        stem or "",
        re.I,
    ):
        return True
    return False


def _answer_references_question(answer: str, qnum: int) -> bool:
    return _stem_references_question(answer, qnum) or bool(
        re.search(rf"\bQ{qnum}\b|\bQ\.?\s*{qnum}\b", answer or "", re.I)
    )


def validate_slot_dependency(
    q: Dict[str, Any],
    dep: SlotDependency,
    *,
    all_questions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Per-question cross-slot dependency validation."""
    stem = (q.get("content") or q.get("question") or "").strip()
    answer = (q.get("correct_answer") or q.get("explanation") or "").strip()
    flags: List[str] = []
    score = 1.0

    if not dep.depends_on_slots:
        return {
            "paper_dependency_score": 1.0,
            "paper_dependency_flags": [],
            "paper_dependency_ok": True,
            "cross_question_depth": 0,
        }

    for prior in dep.must_reference_questions:
        if not _stem_references_question(stem, prior):
            flags.append(f"stem_missing_ref_Q{prior}")
            score -= 0.28

    if dep.required_parts:
        if not _PART_I_RE.search(stem):
            flags.append("missing_part_i")
            score -= 0.2
        if not _PART_II_RE.search(stem):
            flags.append("missing_part_ii_or_hence")
            score -= 0.18

    if dep.ban_scaffolded_chord and _SCAFFOLD_CHORD_RE.search(stem):
        flags.append("scaffolded_chord_in_dependent_stem")
        score -= 0.35

    cite_prior = any(_answer_references_question(answer, p) for p in dep.depends_on_slots)
    if dep.depends_on_slots and not cite_prior and len(answer) > 40:
        flags.append("answer_missing_prior_cite")
        score -= 0.15

    if all_questions and dep.depends_on_slots:
        prior_idx = dep.depends_on_slots[0] - 1
        if 0 <= prior_idx < len(all_questions):
            prior_stem = (all_questions[prior_idx].get("content") or "")[:200]
            r_match = re.search(
                r"\b(\d+)\s*cm\b.*\b(\d+)\s*cm\b", prior_stem, re.I
            )
            if r_match and r_match.group(1) not in stem and r_match.group(2) not in stem:
                flags.append("radii_not_repeated_from_Q1")
                score -= 0.12

    cross_depth = len(dep.depends_on_slots) + (1 if dep.required_parts else 0)
    dep_score = max(0.0, min(1.0, score))
    return {
        "paper_dependency_score": round(dep_score, 3),
        "paper_dependency_flags": flags,
        "paper_dependency_ok": dep_score >= 0.58 and "stem_missing_ref_Q" not in " ".join(flags),
        "cross_question_depth": cross_depth,
        "depends_on_slots": dep.depends_on_slots,
        "derives": dep.derives,
    }


def validate_paper_dependency_chain(
    questions: List[Dict[str, Any]],
    dep_plan: PaperDependencyPlan,
) -> Dict[str, Any]:
    """Validate entire paper chain; attach per-question fields."""
    if not dep_plan.enabled:
        return {"paper_chain_ok": True, "paper_chain_score": 1.0, "paper_chain_flags": []}

    flags: List[str] = []
    scores: List[float] = []
    ordered = sorted(questions, key=lambda x: x.get("order_index", 0))

    for i, q in enumerate(ordered):
        slot_num = i + 1
        dep = dep_plan.slot_dep(slot_num)
        if not dep:
            continue
        report = validate_slot_dependency(q, dep, all_questions=ordered)
        q.update(report)
        scores.append(report["paper_dependency_score"])
        flags.extend(report.get("paper_dependency_flags") or [])

    chain_score = sum(scores) / len(scores) if scores else 1.0
    ok = chain_score >= 0.62 and not any(
        f.startswith("stem_missing_ref_Q") for f in flags
    )
    return {
        "paper_chain_ok": ok,
        "paper_chain_score": round(chain_score, 3),
        "paper_chain_flags": flags,
    }


def _inject_q_reference_prefix(stem: str, prior_slots: List[int]) -> str:
    if not prior_slots:
        return stem
    primary = prior_slots[0]
    if _stem_references_question(stem, primary):
        return stem
    if len(prior_slots) == 1:
        prefix = f"In the same configuration as in Question {primary}, "
    else:
        prefix = (
            f"Using the results from Questions {prior_slots[0]} and {prior_slots[1]}, "
        )
    return prefix + stem


def _ensure_parts_structure(stem: str, dep: SlotDependency) -> str:
    from app.generation.paper_repair import strip_q2_duplicate_chord_part

    if dep.ban_scaffolded_chord:
        return strip_q2_duplicate_chord_part(stem)
    if not dep.required_parts or "(i)" in stem.lower():
        return stem
    return f"(i) {stem} (ii) Hence, complete the remaining part using the above result."


def enforce_slot_stem(
    q: Dict[str, Any],
    dep: SlotDependency,
    *,
    slot_index: int,
) -> Tuple[str, bool]:
    """Post-process stem for dependency compliance."""
    stem = (q.get("content") or q.get("question") or "").strip()
    if not stem or not dep.depends_on_slots:
        return stem, False
    changed = False
    new_stem = stem
    if dep.must_reference_questions:
        prefixed = _inject_q_reference_prefix(new_stem, dep.must_reference_questions)
        if prefixed != new_stem:
            new_stem = prefixed
            changed = True
    if dep.required_parts:
        structured = _ensure_parts_structure(new_stem, dep)
        if structured != new_stem:
            new_stem = structured
            changed = True
    if dep.ban_scaffolded_chord:
        from app.generation.idiomatic_geometry_patterns import remove_scaffolded_chord_length

        cleaned, n = remove_scaffolded_chord_length(new_stem)
        if n:
            new_stem = cleaned
            changed = True
    from app.generation.cross_question_consistency import trim_redundant_q2_reference

    trimmed, tr = trim_redundant_q2_reference(new_stem)
    if tr:
        new_stem = trimmed
        changed = True
    if dep.ban_scaffolded_chord:
        from app.generation.paper_repair import strip_q2_duplicate_chord_part

        stripped = strip_q2_duplicate_chord_part(new_stem)
        if stripped != new_stem:
            new_stem = stripped
            changed = True
    return new_stem.strip(), changed


def _ensure_answer_cites_prior(answer: str, prior_slots: List[int]) -> Tuple[str, bool]:
    if not prior_slots or not answer:
        return answer, False
    if any(_answer_references_question(answer, p) for p in prior_slots):
        return answer, False
    primary = prior_slots[0]
    prefix = f"From Question {primary}, use the earlier concentric radii and chord result. "
    return prefix + answer, True


def apply_paper_dependency_enforcement(
    questions: List[Dict[str, Any]],
    dep_plan: PaperDependencyPlan,
) -> List[Dict[str, Any]]:
    """Enforce dependency wording on stems and model answers."""
    if not dep_plan.enabled:
        return questions
    out: List[Dict[str, Any]] = []
    ordered = sorted(
        questions,
        key=lambda x: (int(x.get("slot_number") or 0), x.get("order_index", 0)),
    )
    for q in ordered:
        q = dict(q)
        slot_num = int(q.get("slot_number") or 0)
        if slot_num < 1:
            slot_num = int(q.get("order_index", 0)) + 1
        dep = dep_plan.slot_dep(slot_num)
        if dep:
            new_stem, stem_changed = enforce_slot_stem(q, dep, slot_index=slot_num - 1)
            if stem_changed:
                q["content"] = new_stem
                q["idiom_fixed"] = True
                q["dependency_enforced"] = True
            ans = (q.get("correct_answer") or "").strip()
            if dep.depends_on_slots:
                new_ans, ans_changed = _ensure_answer_cites_prior(ans, dep.depends_on_slots)
                if ans_changed:
                    q["correct_answer"] = new_ans
                    q["dependency_enforced"] = True
        from app.generation.paper_repair import sanitize_question_fields

        out.append(sanitize_question_fields(q))
    return out


def should_reject_paper_dependency(q: Dict[str, Any], *, ui_difficulty: str = "medium") -> bool:
    if (ui_difficulty or "").lower() not in ("hard", "difficult"):
        return False
    if "paper_dependency_score" not in q:
        return False
    flags = q.get("paper_dependency_flags") or []
    if "scaffolded_chord_in_dependent_stem" in flags:
        return True
    if "stem_missing_ref_Q1" in flags or "stem_missing_ref_Q2" in flags:
        return True
    return not q.get("paper_dependency_ok", True)


def merge_dependency_into_slot_meta(
    slot_meta: List[Dict[str, Any]],
    dep_plan: PaperDependencyPlan,
) -> List[Dict[str, Any]]:
    if not dep_plan.enabled:
        return slot_meta
    out = [dict(m) for m in slot_meta]
    for dep in dep_plan.slots:
        idx = dep.slot - 1
        if idx < len(out):
            out[idx]["depends_on_slots"] = dep.depends_on_slots
            out[idx]["paper_derives"] = dep.derives
            out[idx]["required_parts"] = list(dep.required_parts)
            out[idx]["ban_scaffolded_chord"] = dep.ban_scaffolded_chord
    return out


def plan_to_dict(dep_plan: PaperDependencyPlan) -> Dict[str, Any]:
    if not dep_plan.enabled:
        return {"enabled": False}
    return {
        "enabled": True,
        "chapter": dep_plan.chapter,
        "slots": [
            {
                "slot": s.slot,
                "depends_on": s.depends_on_slots,
                "derives": s.derives,
                "required_parts": list(s.required_parts),
            }
            for s in dep_plan.slots
        ],
    }
