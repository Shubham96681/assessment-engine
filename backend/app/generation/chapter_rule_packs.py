"""
Chapter rule packs — single source of truth per locked chapter.

Used by SemanticGenerationPlan and PromptCompiler (no global geometry DNA).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.generation.strict_topic_gate import CHAPTER_FORBIDDEN


@dataclass(frozen=True)
class SlotPlanRow:
    """One blueprint slot — declarative data on ChapterRulePack."""

    archetype_id: str
    band: str
    role: str
    max_marks: Optional[int] = None


@dataclass(frozen=True)
class OrBranchWeights:
    """Structural OR difficulty signals (chapter-agnostic defaults, overridable per pack)."""

    prove: float = 3.0
    compound_identity: float = 2.0
    reduction_only: float = 0.8
    large_angle_reduction: float = 0.5


@dataclass(frozen=True)
class ProofRouteRule:
    """Stem must use the listed identity family (data-driven, not chapter branches)."""

    stem_needle: str
    required_phrase: str
    forbidden_phrase: str = ""


@dataclass(frozen=True)
class StemPatternCap:
    """Cap repeated stem skeletons (e.g. degree→radian + quadrant + sin/cos)."""

    pattern: str
    max_count: int


@dataclass(frozen=True)
class DifficultyEscalationConfig:
    """RD Sharma / JEE-style elevation hints — registered per chapter on the rule pack."""

    tier_labels: Tuple[str, ...] = ("foundation", "rd_sharma", "jee_foundation")
    prompt_lines: Tuple[str, ...] = ()
    min_identity_proof_items: int = 0
    min_prove_hence_chains: int = 0
    require_balanced_or: bool = False
    forbid_trivial_quadrant: Tuple[str, ...] = ()
    prove_stem_pattern: str = r"\bprove\b"
    hence_stem_pattern: str = r"\bhence\b"
    ratio_find_stem_pattern: str = ""
    all_ratios_stem_pattern: str = ""

    @property
    def enabled(self) -> bool:
        return bool(
            self.prompt_lines
            or self.min_identity_proof_items
            or self.min_prove_hence_chains
            or self.forbid_trivial_quadrant
        )


@dataclass(frozen=True)
class ChapterPaperQualityConfig:
    """
    Per-chapter paper quality rules — register on ChapterRulePack, not in validators.
    """

    max_per_skill_family: Tuple[Tuple[str, int], ...] = ()
    slot_plans: Tuple[Tuple[int, Tuple[SlotPlanRow, ...]], ...] = ()
    standard_exact_degree_step: int = 0
    forbid_minute_with_exact_surd: bool = False
    max_or_difficulty_ratio: float = 0.0
    prompt_bullets: Tuple[str, ...] = ()
    or_branch_weights: OrBranchWeights = field(default_factory=OrBranchWeights)
    proof_route_rules: Tuple[ProofRouteRule, ...] = ()
    stem_pattern_caps: Tuple[StemPatternCap, ...] = ()
    critical_issue_tokens: Tuple[str, ...] = ()
    reject_flag_prefixes: Tuple[str, ...] = ()
    max_marks_inflated_reject: int = 0

    @property
    def enabled(self) -> bool:
        return bool(
            self.max_per_skill_family
            or self.slot_plans
            or self.standard_exact_degree_step > 0
            or self.forbid_minute_with_exact_surd
            or self.max_or_difficulty_ratio > 0
            or self.prompt_bullets
        )

    def max_family_dict(self) -> Dict[str, int]:
        return dict(self.max_per_skill_family)

    def slot_plan_for_count(self, n: int) -> Tuple[SlotPlanRow, ...]:
        for count, rows in self.slot_plans:
            if count == n:
                return rows
        return ()


def _resolve_pack_paper_quality(
    chapter_key: str,
    explicit: Optional[ChapterPaperQualityConfig],
) -> Optional[ChapterPaperQualityConfig]:
    if explicit is not None:
        return explicit
    from app.generation.chapter_quality_registry import paper_quality_for

    return paper_quality_for(chapter_key)


def _resolve_pack_escalation(
    chapter_key: str,
    explicit: Optional[DifficultyEscalationConfig],
) -> Optional[DifficultyEscalationConfig]:
    if explicit is not None:
        return explicit
    from app.generation.chapter_quality_registry import escalation_for

    return escalation_for(chapter_key)


@dataclass(frozen=True)
class ChapterRulePack:
    """
    Declarative chapter intelligence — extend by data, not procedural branches.

    embedding_anchors: exemplar stems for semantic purity centroid (paraphrase detection).
    """

    chapter_key: str
    display_title: str
    forbidden_terms: Tuple[str, ...]
    archetype_ids: Tuple[str, ...]
    theorem_pattern_ids: Tuple[str, ...]
    figure_types: Tuple[str, ...]
    hard_difficulty_patterns: Tuple[str, ...]
    cognitive_blueprint_5: Tuple[str, ...]
    embedding_anchors: Tuple[str, ...]
    stem_example: str
    rag_style_note: str
    preferred_question_types: Tuple[str, ...] = (
        "ShortAnswer",
        "LongAnswer",
        "MCQ",
        "CaseStudy",
    )
    max_figure_based_count: int = 1
    retrieval_semantic_terms: Tuple[str, ...] = ()
    author_style_line: str = ""
    semantic_completeness_text: str = ""
    preferred_types_figure_note: str = ""
    uniqueness_variation_hint: str = ""
    imperfection_profile_key: str = ""
    full_hard_reject_pythagoras_drill: bool = False
    paper_quality: Optional[ChapterPaperQualityConfig] = None
    difficulty_escalation: Optional[DifficultyEscalationConfig] = None

    @property
    def uses_concentric_uniqueness(self) -> bool:
        return "concentric" in self.archetype_ids

    def forbidden_block(self) -> str:
        terms = ", ".join(self.forbidden_terms[:14])
        return f"Do NOT use in any stem, figure, or answer: {terms}."

    def figure_types_block(self) -> str:
        return "Allowed figure types: " + ", ".join(self.figure_types) + "."

    def hard_mode_block(self, ui_difficulty: str, *, full_hard: bool = False) -> str:
        from app.generation.chapter_prompt_isolation import build_chapter_hard_prompt_stack

        ui = (ui_difficulty or "medium").lower()
        if ui not in ("hard", "difficult"):
            return ""
        return build_chapter_hard_prompt_stack(
            self.chapter_key, ui, full_hard=full_hard
        ).strip()

    def numeric_rules_block(self) -> str:
        from app.generation.chapter_prompt_isolation import numeric_prompt_block

        return numeric_prompt_block(self.chapter_key).strip()

    def reasoning_diversity_block(
        self,
        *,
        question_count: int = 5,
        paper_template_id: Optional[str] = None,
        ui_difficulty: str = "hard",
        full_hard: bool = False,
    ) -> str:
        from app.generation.chapter_prompt_isolation import reasoning_diversity_prompt_block

        return reasoning_diversity_prompt_block(
            self.chapter_key,
            question_count,
            paper_template_id=paper_template_id,
            ui_difficulty=ui_difficulty,
            full_hard=full_hard,
        ).strip()

    def idiomatic_block(self) -> str:
        from app.generation.chapter_prompt_isolation import idiomatic_prompt_block

        return idiomatic_prompt_block(self.chapter_key).strip()

    def archetype_table(self) -> str:
        """Chapter-scoped ids only — never global CIRCLE_ARCHETYPES table."""
        lines = ["| Archetype id | Use |", "|--------------|-----|"]
        for aid in self.archetype_ids:
            lines.append(f"| {aid} | allowed |")
        return "\n".join(lines)

    def compact_blueprint(
        self,
        slots: Sequence[Any],
        *,
        ui_difficulty: str,
        full_hard: bool = False,
    ) -> str:
        """Slot order from plan — no legacy build_paper_blueprint geometry."""
        lines = [
            f"EXERCISE BLUEPRINT — {self.display_title} (ids 1..N):",
            f"Chapter fingerprint: {self.chapter_key} (ONLY these archetypes).",
        ]
        if ui_difficulty.lower() in ("hard", "difficult"):
            if full_hard:
                lines.append("FULL HARD (100%): every slot band L5 — hardest tier only.")
                if self.chapter_key == "trigonometry":
                    from app.generation.trigonometry_hard_benchmark import (
                        suggested_paper_totals,
                    )

                    tot = suggested_paper_totals(len(slots) or 10)
                    lines.append(
                        f"BENCHMARK MARKS: {tot['marks_per_slot_default']} per slot "
                        f"(last slot {tot['marks_per_slot_default'] + 2} if count≥8); "
                        f"target total ≈ {tot['total_marks']} for {tot['total_questions']} questions."
                    )
            else:
                lines.append("Hardness = chapter patterns below (not geometry-global).")
        for s in slots:
            slot_num = getattr(s, "slot", None) or s.get("slot", 0)
            band = getattr(s, "band", None) or s.get("band", "L3")
            arch = getattr(s, "archetype_id", None) or s.get("archetype_id", "")
            cog = getattr(s, "cognitive_type", None) or s.get("cognitive_type", "")
            role = getattr(s, "role", None) or s.get("role", "")
            fig = getattr(s, "figure_hint", None) or s.get("figure_hint", "")
            stem_fmt = getattr(s, "stem_format", None) or s.get("stem_format", "")
            fmt_note = f" | stem_format={stem_fmt}" if stem_fmt else ""
            lines.append(
                f'  id "{slot_num}": [{arch}] band {band} | {cog}'
                + fmt_note
                + (f" | figure: {fig}" if fig else "")
            )
        stem_len = (
            "STEM LENGTH: L5 HOTS 35–60 words on multi-part slots; sparse/direct slots 12–28 words."
            if full_hard
            else "STEM LENGTH: L1 12–25 | L2–L3 20–40 | L5 HOTS 35–60 words."
        )
        lines.extend(
            [
                "",
                stem_len,
                "TRAPS: invisible in stem; theorems named only in answers.",
            ]
        )
        if self.chapter_key == "trigonometry" or full_hard:
            from app.generation.stem_pattern_variety import (
                assign_stem_patterns,
                stem_pattern_prompt_block,
            )

            pats = [
                getattr(s, "stem_format", None) or s.get("stem_format", "")
                for s in slots
            ]
            if not any(pats):
                pats = assign_stem_patterns(
                    len(slots) or 5,
                    chapter=self.chapter_key,
                    full_hard=full_hard,
                )
            roles = [getattr(s, "role", None) or s.get("role", "") for s in slots]
            lines.extend(["", stem_pattern_prompt_block(pats, roles=roles)])
        from app.generation.chapter_paper_quality import chapter_paper_quality_prompt_block

        qc = chapter_paper_quality_prompt_block(
            self.chapter_key,
            len(slots) or 5,
            ui_difficulty=ui_difficulty,
            full_hard=full_hard,
        )
        if qc:
            lines.extend(["", qc])
        esc = self.difficulty_escalation
        if esc and esc.enabled:
            from app.generation.difficulty_escalation import escalation_prompt_block

            block = escalation_prompt_block(self.chapter_key)
            if block:
                lines.extend(["", block])
        return "\n".join(lines)

    def semantic_completeness_rules(self) -> str:
        return self.semantic_completeness_text.strip() or (
            "SEMANTIC COMPLETENESS:\n- Stems self-contained; all givens in text."
        )

    def author_style_note(self) -> str:
        return self.author_style_line.strip() or (
            "AUTHOR STYLE: compressed textbook stems; uneven marks; invisible traps."
        )

    def preferred_types_block(self) -> str:
        types = ", ".join(self.preferred_question_types)
        figure_note = self.preferred_types_figure_note.strip() or (
            f"- Max {self.max_figure_based_count} FigureBased when the chapter needs a diagram."
        )
        return (
            f"PREFERRED QUESTION TYPES ({self.display_title}): {types}.\n"
            f"{figure_note}"
        )

    def uniqueness_refresh_line(self) -> str:
        return self.uniqueness_variation_hint.strip() or (
            f"- Change givens and labels every generation ({self.display_title})"
        )

    def preferred_type_for_slot(self, slot_index: int) -> str:
        """0-based slot index → question type from pack data."""
        types = tuple(self.preferred_question_types) or ("LongAnswer",)
        t = types[slot_index % len(types)]
        if t == "FigureBased" and self.max_figure_based_count <= 0:
            return "LongAnswer"
        return t


def _pack(
    key: str,
    title: str,
    forbidden: Tuple[str, ...],
    archetypes: Tuple[str, ...],
    theorems: Tuple[str, ...],
    figures: Tuple[str, ...],
    hard_patterns: Tuple[str, ...],
    cognitive: Tuple[str, ...],
    embedding_anchors: Tuple[str, ...],
    example: str,
    rag_note: str,
    preferred_question_types: Tuple[str, ...] = (
        "ShortAnswer",
        "LongAnswer",
        "MCQ",
        "CaseStudy",
    ),
    max_figure_based_count: int = 1,
    retrieval_semantic_terms: Tuple[str, ...] = (),
    *,
    author_style_line: str = "",
    semantic_completeness_text: str = "",
    preferred_types_figure_note: str = "",
    uniqueness_variation_hint: str = "",
    imperfection_profile_key: str = "",
    full_hard_reject_pythagoras_drill: bool = False,
    paper_quality: Optional[ChapterPaperQualityConfig] = None,
    difficulty_escalation: Optional[DifficultyEscalationConfig] = None,
) -> ChapterRulePack:
    extra = tuple(sorted(CHAPTER_FORBIDDEN.get(key, set())))[:8]
    merged = tuple(dict.fromkeys(forbidden + extra))
    return ChapterRulePack(
        chapter_key=key,
        display_title=title,
        forbidden_terms=merged,
        archetype_ids=archetypes,
        theorem_pattern_ids=theorems,
        figure_types=figures,
        hard_difficulty_patterns=hard_patterns,
        cognitive_blueprint_5=cognitive,
        embedding_anchors=embedding_anchors,
        stem_example=example,
        rag_style_note=rag_note,
        preferred_question_types=preferred_question_types,
        max_figure_based_count=max_figure_based_count,
        retrieval_semantic_terms=retrieval_semantic_terms,
        author_style_line=author_style_line,
        semantic_completeness_text=semantic_completeness_text,
        preferred_types_figure_note=preferred_types_figure_note,
        uniqueness_variation_hint=uniqueness_variation_hint,
        imperfection_profile_key=imperfection_profile_key,
        full_hard_reject_pythagoras_drill=full_hard_reject_pythagoras_drill,
        paper_quality=_resolve_pack_paper_quality(key, paper_quality),
        difficulty_escalation=_resolve_pack_escalation(key, difficulty_escalation),
    )


def _load_chapter_quality_registry() -> None:
    """Import registry module so chapter profiles register before pack lookup."""
    from app.generation import chapter_quality_registry  # noqa: F401


_load_chapter_quality_registry()


CHAPTER_RULES: Dict[str, ChapterRulePack] = {
    "quadratic": _pack(
        "quadratic",
        "Quadratic Equations",
        ("circle", "tangent", "secant", "radius", "chord", "concentric", "aob", "centre", "center"),
        (
            "factorisation_roots",
            "nature_of_roots",
            "equal_roots_k",
            "word_problem_area",
            "formula_roots",
            "hots_quad",
        ),
        (
            "discriminant_nature",
            "equal_roots_parameter",
            "factorisation_method",
            "quadratic_formula",
            "area_word_problem",
        ),
        ("labeled_diagram", "table", "line_graph", "flowchart"),
        (
            "parameter k traps",
            "discriminant traps",
            "symbolic roots",
            "word-problem modelling",
            "multi-case reasoning",
        ),
        (
            "direct factorisation / coefficient trap",
            "discriminant + nature of roots",
            "parameter k or equal roots",
            "area or speed word problem",
            "HOTS fusion / OR / disguised reuse",
        ),
        (
            "Solve x² − 7x + 10 = 0 by factorisation.",
            "Find the nature of roots of 2x² − 5x + 3 = 0.",
            "Find k if 3x² + kx + 12 = 0 has equal roots.",
            "Length is twice breadth; area 800 m². Form the quadratic and find x.",
            "A train covers 60 km at v km/h; return takes 1 h longer. Find v.",
        ),
        "Find the nature of roots of 2x² − 5x + 3 = 0.",
        "Match compression and step depth of quadratic exercises in SOURCE — do not copy stems.",
        preferred_question_types=(
            "ShortAnswer",
            "ShortAnswer",
            "LongAnswer",
            "CaseStudy",
            "MCQ",
        ),
        max_figure_based_count=1,
        retrieval_semantic_terms=(
            "quadratic equation factorisation",
            "discriminant nature of roots",
            "equal roots parameter k",
            "word problem area speed",
        ),
        author_style_line=(
            "AUTHOR STYLE: compressed algebra stems; area/speed word models; "
            "uneven marks; exercise memory teach→reuse — no geometry diagrams."
        ),
        semantic_completeness_text=(
            "SEMANTIC COMPLETENESS (quadratic):\n"
            "- State equation or word-model givens; Find/Show that with numbers.\n"
            "- If stem says 'the equation', the quadratic must appear in the stem or table.\n"
            "- FigureBased only for area/speed models or coefficient tables — not bare factorisation.\n"
            "- OR: same archetype, separate numeric givens per branch.\n"
            "- L4/L5: model answer needs 3+ dependent steps (form → discriminant/factor → roots → verify).\n"
            "- BAN circle/tangent vocabulary."
        ),
        preferred_types_figure_note=(
            "- Max 1 FigureBased item(s) — only rectangle/segment layout, coefficient table, "
            "or line_graph when required.\n"
            "- Prefer ShortAnswer, LongAnswer, CaseStudy, MCQ for bare algebra."
        ),
        uniqueness_variation_hint=(
            "- Change coefficients, parameters k, and word-problem numbers every generation"
        ),
    ),
    "circles": _pack(
        "circles",
        "Circles",
        ("discriminant", "quadratic equation", "parallelogram", "rhombus"),
        (
            "length_find",
            "angle_theorem",
            "hidden_theorem",
            "concentric",
            "chord_tangent",
            "secant_tangent",
            "hots_mixed",
            "cyclic_angle",
            "converse_identify",
            "direct_theorem",
            "common_tangent",
            "tangent_similarity",
        ),
        (
            "tangent_radius_perpendicular",
            "tangent_lengths_equal",
            "secant_tangent_power",
            "concentric_chord",
            "angle_in_alternate_segment",
        ),
        ("labeled_diagram",),
        (
            "tangent–secant fusion",
            "cyclic angle chase",
            "power of a point",
            "concentric reasoning",
        ),
        (
            "hidden length / concentric / chord",
            "theorem chain — chord–tangent or cyclic",
            "sparse hard proof",
            "multi-concept secant+tangent",
            "HOTS fusion / disguised reuse",
        ),
        (
            "PQ is a tangent at P to a circle with centre O. OP = 5 cm, OQ = 12 cm. Find PQ.",
            "Tangents TA, TB from T. If angle ATB = 60°, find angle AOB.",
            "Prove that tangents from an external point are equal.",
            "Concentric circles radii 7 cm and 4 cm. Find chord of larger touching smaller.",
            "From T, secant TCD and tangent TE. If TC = 3 cm and TD = 27 cm, find TE.",
        ),
        "PQ is a tangent at P. O is centre, OP = 5 cm, OQ = 12 cm. Find PQ.",
        "Match tangent/secant exercise style in SOURCE — vary labels and numbers only.",
        preferred_question_types=(
            "FigureBased",
            "FigureBased",
            "FigureBased",
            "FigureBased",
            "FigureBased",
        ),
        max_figure_based_count=5,
        retrieval_semantic_terms=(
            "tangent perpendicular to radius",
            "equal tangents from external point",
            "secant and tangent length",
            "concentric circles chord",
            "angle between tangents",
            "power of a point tangent secant",
            "chord touching smaller circle",
        ),
        author_style_line=(
            "AUTHOR STYLE: compressed stems; dashed radii; symmetric tangents TA, TB; "
            "uneven marks; exercise memory teach→reuse on last slot."
        ),
        semantic_completeness_text=(
            "SEMANTIC COMPLETENESS (circles):\n"
            "- Find angle: full angle symbol + numeric given.\n"
            "- Tangent length: name point of contact, centre, segments.\n"
            "- Prove equal tangents: name external point and both tangents."
        ),
        preferred_types_figure_note=(
            "- At least 4 of 5 items MUST be FigureBased with figure_spec (labeled_diagram).\n"
            "- Each FigureBased stem: centre O, dashed radii to contacts, tangents/secants marked.\n"
            "- L4/L5 FigureBased: (i)(ii) sub-parts or fusion — not a one-line find."
        ),
        uniqueness_variation_hint=(
            "- Change radii pairs, tangent lengths, and external point names every generation"
        ),
        imperfection_profile_key="rd_sharma",
        full_hard_reject_pythagoras_drill=True,
    ),
    "quadrilaterals": _pack(
        "quadrilaterals",
        "Quadrilaterals",
        ("circle", "tangent", "secant", "radius", "concentric", "discriminant"),
        (
            "parallelogram_opposite",
            "diagonal_bisect",
            "midpoint_theorem",
            "rhombus_diagonal",
            "area_quad",
            "hots_quad",
        ),
        (
            "parallelogram_diagonal_bisect",
            "midpoint_theorem",
            "rhombus_diagonals",
        ),
        ("labeled_diagram", "table"),
        ("proof + Hence", "diagonal properties", "midpoint chain", "area find"),
        (
            "opposite sides / angles",
            "diagonal bisection",
            "midpoint theorem",
            "rhombus or area",
            "HOTS prove + Hence",
        ),
        (
            "In parallelogram ABCD, if angle A = 72°, find angle C.",
            "Diagonals of parallelogram PQRS meet at O. If AO = 7 cm, find AC.",
            "Prove that diagonals of a rhombus are perpendicular.",
            "Trapezium ABCD has AB parallel DC. Find the length of mid-segment.",
            "Prove opposite sides of a parallelogram are equal. Hence find a side.",
        ),
        "In parallelogram ABCD, if angle A = 72°, find angle C.",
        "Match quadrilateral proof/find style in SOURCE.",
        preferred_question_types=(
            "FigureBased",
            "ShortAnswer",
            "LongAnswer",
            "ShortAnswer",
            "FigureBased",
        ),
        max_figure_based_count=3,
        preferred_types_figure_note=(
            "- Up to 3 FigureBased: parallelogram/rhombus diagrams.\n"
            "- Proofs and finds may be ShortAnswer/LongAnswer without a figure."
        ),
        uniqueness_variation_hint=(
            "- Change vertex labels, diagonal lengths, and angle givens every generation"
        ),
        full_hard_reject_pythagoras_drill=True,
    ),
    "triangles": _pack(
        "triangles",
        "Triangles",
        ("circle", "tangent", "secant", "radius", "concentric", "discriminant", "quadratic"),
        (
            "similarity_ratio",
            "congruence_rhs",
            "pythagoras_find",
            "area_ratio",
            "proof_derive",
            "hots_triangle",
        ),
        ("similar_triangles", "pythagoras", "congruence"),
        ("labeled_diagram",),
        ("hidden similarity", "ratio chain", "proof+Hence"),
        (
            "similarity anchor",
            "Hence ratio",
            "congruence proof",
            "area from ratio",
            "HOTS fusion",
        ),
        (
            "In triangle PQR, DE parallel QR meets PQ at D and PR at E. If PD = 4 cm and DQ = 6 cm, find PE : ER.",
            "Prove triangles ABC and DEF congruent by SAS.",
        ),
        "In triangle PQR, DE parallel QR meets PQ at D and PR at E. If PD = 4 cm and DQ = 6 cm, find PE : ER.",
        "Match triangle similarity and congruence style in SOURCE.",
        preferred_question_types=("FigureBased", "ShortAnswer", "LongAnswer", "ShortAnswer", "FigureBased"),
        max_figure_based_count=3,
        uniqueness_variation_hint=(
            "- Change similarity ratios, corresponding sides, and proof labels every generation"
        ),
        full_hard_reject_pythagoras_drill=True,
    ),
    "trigonometry": _pack(
        "trigonometry",
        "Trigonometry",
        ("circle", "secant", "concentric", "parallelogram", "discriminant", "quadratic equation"),
        (
            "standard_angle",
            "identity_prove",
            "quadrant_reduction",
            "ratio_find",
            "radian_degree",
            "hots_trig",
        ),
        ("pythagorean_identity", "quadrant_signs", "complementary_angles"),
        ("labeled_diagram", "table"),
        ("identity chain", "quadrant trap", "standard value"),
        (
            "radian conversion",
            "identity proof",
            "quadrant sign",
            "ratio from one function",
            "HOTS identity fusion",
        ),
        (
            "Express 75° in radian measure.",
            "If sin θ = 3/5 and θ lies in quadrant II, find cos θ.",
            "Prove that (1 + tan²θ) sec²θ = 1.",
        ),
        "Express 75° in radian measure.",
        "Match trigonometric identity and reduction style in SOURCE.",
        preferred_question_types=("ShortAnswer", "ShortAnswer", "LongAnswer", "ShortAnswer", "LongAnswer"),
        max_figure_based_count=1,
        preferred_types_figure_note=(
            "- Max 1 FigureBased when a quadrant sketch or ratio table is needed.\n"
            "- Prefer ShortAnswer and LongAnswer for reductions, proofs, and ratio finds."
        ),
        uniqueness_variation_hint=(
            "- Change angles, quadrants, and standard-ratio constants every generation"
        ),
    ),
}

GENERIC_RULES = _pack(
    "generic",
    "Selected Chapter",
    (),
    ("numerical_find", "concept_apply", "word_problem", "multi_step", "hots_fusion"),
    (),
    ("labeled_diagram", "flowchart", "table"),
    ("multi-step inference", "word problem", "proof or find"),
    (
        "direct application",
        "variation",
        "sparse hard",
        "conceptual",
        "HOTS challenge",
    ),
    ("Apply the main idea from the chapter to find the unknown.",),
    "Given values from the chapter, calculate the required quantity.",
    "Match style and depth of SOURCE exercises — original stems only.",
    preferred_question_types=("ShortAnswer", "LongAnswer", "MCQ", "CaseStudy", "FigureBased"),
    max_figure_based_count=2,
)


def get_chapter_rule_pack(chapter: str) -> ChapterRulePack:
    key = (chapter or "generic").strip().lower()
    return CHAPTER_RULES.get(key, GENERIC_RULES)
