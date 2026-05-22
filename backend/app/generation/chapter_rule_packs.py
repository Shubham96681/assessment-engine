"""
Chapter rule packs — single source of truth per locked chapter.

Used by SemanticGenerationPlan and PromptCompiler (no global geometry DNA).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from app.generation.strict_topic_gate import CHAPTER_FORBIDDEN


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

    def forbidden_block(self) -> str:
        terms = ", ".join(self.forbidden_terms[:14])
        return f"Do NOT use in any stem, figure, or answer: {terms}."

    def figure_types_block(self) -> str:
        return "Allowed figure types: " + ", ".join(self.figure_types) + "."

    def hard_mode_block(self, ui_difficulty: str) -> str:
        from app.generation.chapter_prompt_isolation import build_chapter_hard_prompt_stack

        ui = (ui_difficulty or "medium").lower()
        if ui not in ("hard", "difficult"):
            return ""
        return build_chapter_hard_prompt_stack(self.chapter_key, ui).strip()

    def numeric_rules_block(self) -> str:
        from app.generation.chapter_prompt_isolation import numeric_prompt_block

        return numeric_prompt_block(self.chapter_key).strip()

    def reasoning_diversity_block(self) -> str:
        from app.generation.chapter_prompt_isolation import reasoning_diversity_prompt_block

        return reasoning_diversity_prompt_block(self.chapter_key).strip()

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
    ) -> str:
        """Slot order from plan — no legacy build_paper_blueprint geometry."""
        lines = [
            f"EXERCISE BLUEPRINT — {self.display_title} (ids 1..N):",
            f"Chapter fingerprint: {self.chapter_key} (ONLY these archetypes).",
        ]
        if ui_difficulty.lower() in ("hard", "difficult"):
            lines.append("Hardness = chapter patterns below (not geometry-global).")
        for s in slots:
            slot_num = getattr(s, "slot", None) or s.get("slot", 0)
            band = getattr(s, "band", None) or s.get("band", "L3")
            arch = getattr(s, "archetype_id", None) or s.get("archetype_id", "")
            cog = getattr(s, "cognitive_type", None) or s.get("cognitive_type", "")
            role = getattr(s, "role", None) or s.get("role", "")
            fig = getattr(s, "figure_hint", None) or s.get("figure_hint", "")
            lines.append(
                f'  id "{slot_num}": [{arch}] band {band} | {cog}'
                + (f" | figure: {fig}" if fig else "")
            )
        lines.extend(
            [
                "",
                "STEM LENGTH: L1 12–25 | L2–L3 20–40 | L5 HOTS 35–60 words.",
                "TRAPS: invisible in stem; theorems named only in answers.",
            ]
        )
        return "\n".join(lines)

    def semantic_completeness_rules(self) -> str:
        if self.chapter_key == "quadratic":
            return (
                "SEMANTIC COMPLETENESS (quadratic):\n"
                "- State equation or word-model givens; Find/Show that with numbers.\n"
                "- If stem says 'the equation', the quadratic must appear in the stem or table.\n"
                "- FigureBased only for area/speed models or coefficient tables — not bare factorisation.\n"
                "- OR: same archetype, separate numeric givens per branch.\n"
                "- L4/L5: model answer needs 3+ dependent steps (form → discriminant/factor → roots → verify).\n"
                "- BAN circle/tangent vocabulary."
            )
        if self.chapter_key == "circles":
            return (
                "SEMANTIC COMPLETENESS (circles):\n"
                "- Find angle: full angle symbol + numeric given.\n"
                "- Tangent length: name point of contact, centre, segments.\n"
                "- Prove equal tangents: name external point and both tangents."
            )
        return (
            "SEMANTIC COMPLETENESS:\n"
            "- Stems self-contained; all givens in text."
        )

    def author_style_note(self) -> str:
        if self.chapter_key == "circles":
            return (
                "AUTHOR STYLE: compressed stems; dashed radii; symmetric tangents TA, TB; "
                "uneven marks; exercise memory teach→reuse on last slot."
            )
        if self.chapter_key == "quadratic":
            return (
                "AUTHOR STYLE: compressed algebra stems; area/speed word models; "
                "uneven marks; exercise memory teach→reuse — no geometry diagrams."
            )
        return "AUTHOR STYLE: compressed textbook stems; uneven marks; invisible traps."

    def preferred_types_block(self) -> str:
        types = ", ".join(self.preferred_question_types)
        if self.chapter_key == "circles":
            figure_note = (
                f"- FigureBased is primary for Circles (up to {self.max_figure_based_count} items): "
                "labeled_diagram with centre, radii (dashed), tangents (solid), angles marked.\n"
                "- ShortAnswer/LongAnswer for proofs and numeric finds without over-drawing."
            )
        elif self.chapter_key == "quadratic":
            figure_note = (
                f"- Max {self.max_figure_based_count} FigureBased item(s) — "
                "only rectangle/segment layout, coefficient table, or line_graph when required.\n"
                "- Prefer ShortAnswer, LongAnswer, CaseStudy, MCQ for bare algebra."
            )
        elif self.chapter_key == "quadrilaterals":
            figure_note = (
                f"- Up to {self.max_figure_based_count} FigureBased: parallelogram/rhombus diagrams.\n"
                "- Proofs and finds may be ShortAnswer/LongAnswer without a figure."
            )
        else:
            figure_note = (
                f"- Max {self.max_figure_based_count} FigureBased when the chapter needs a diagram."
            )
        return (
            f"PREFERRED QUESTION TYPES ({self.display_title}): {types}.\n"
            f"{figure_note}"
        )


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
    )


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
            "ShortAnswer",
            "LongAnswer",
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
