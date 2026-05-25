"""
Per-chapter paper quality and escalation profiles — declarative data only.

Validators import via get_chapter_rule_pack(); this module registers profiles by chapter_key.
Add new chapters here (or split into JSON later) without editing validator logic.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from app.generation.chapter_rule_packs import (
    ChapterPaperQualityConfig,
    DifficultyEscalationConfig,
    OrBranchWeights,
    ProofRouteRule,
    SlotPlanRow,
    StemPatternCap,
)

_DEFAULT_CRITICAL_TOKENS: Tuple[str, ...] = (
    "exact_surd_with_minute",
    "non_standard_exact_angle",
    "or_branch_imbalance",
    "or_branch_trivial",
    "skill_family_cap",
    "marks_inflated",
    "empty_stem",
    "proof_route_",
    "stem_pattern_excess",
    "trivial_quadrant",
    "too_few_proofs",
    "too_few_hence",
)

_DEFAULT_REJECT_PREFIXES: Tuple[str, ...] = (
    "exact_surd_with_minute",
    "non_standard_exact",
    "or_branch_",
    "marks_inflated",
    "proof_route_",
    "empty_stem",
)

_PAPER_QUALITY: Dict[str, ChapterPaperQualityConfig] = {}
_ESCALATION: Dict[str, DifficultyEscalationConfig] = {}


def register_paper_quality(key: str, cfg: ChapterPaperQualityConfig) -> None:
    _PAPER_QUALITY[(key or "").strip().lower()] = cfg


def register_escalation(key: str, cfg: DifficultyEscalationConfig) -> None:
    _ESCALATION[(key or "").strip().lower()] = cfg


def paper_quality_for(chapter: str) -> Optional[ChapterPaperQualityConfig]:
    return _PAPER_QUALITY.get((chapter or "").strip().lower())


def escalation_for(chapter: str) -> Optional[DifficultyEscalationConfig]:
    return _ESCALATION.get((chapter or "").strip().lower())


def _register_trigonometry() -> None:
    register_escalation(
        "trigonometry",
        DifficultyEscalationConfig(
            tier_labels=("foundation", "rd_sharma", "jee_foundation"),
            prompt_lines=(
                "Prefer prove-then-hence chains over bare value recall.",
                "Include at least one hidden-condition ratio item (e.g. sin θ + cos θ given, find tan θ).",
                "OR branches: equal steps on both paths (both prove+find or both multi-step reductions).",
                "Avoid quadrant I-only ratio finds when signs are trivial — use QII/QIII/QIV.",
                "Add one reduction-maze or general-solution style item when count ≥ 8.",
            ),
            min_identity_proof_items=2,
            min_prove_hence_chains=2,
            require_balanced_or=True,
            forbid_trivial_quadrant=("lies in quadrant I", "quadrant I,"),
            prove_stem_pattern=r"\bprove\b",
            hence_stem_pattern=r"\bhence\b",
            ratio_find_stem_pattern=r"\bfind\b.*\b(sin|cos|tan|cot|sec|cosec)\b",
            all_ratios_stem_pattern=r"\b(all|other|remaining)\s+ratios?\b",
        ),
    )
    register_paper_quality(
        "trigonometry",
        ChapterPaperQualityConfig(
            max_per_skill_family=(
                ("period_reduction", 2),
                ("identity_proof", 3),
            ),
            slot_plans=(
                (
                    5,
                    (
                        SlotPlanRow("radian_degree", "L3", "radian conversion"),
                        SlotPlanRow("identity_prove", "L3", "identity proof"),
                        SlotPlanRow("ratio_find", "L3", "ratio from one function"),
                        SlotPlanRow("quadrant_reduction", "L3", "period reduction with quadrant"),
                        SlotPlanRow("hots_trig", "L5", "HOTS prove + apply OR balanced alternative"),
                    ),
                ),
                (
                    10,
                    (
                        SlotPlanRow(
                            "radian_degree",
                            "L3",
                            "Degree–radian conversion + quadrant for standard angle",
                        ),
                        SlotPlanRow(
                            "identity_prove",
                            "L3",
                            "Prove one compound-angle identity",
                        ),
                        SlotPlanRow(
                            "ratio_find",
                            "L3",
                            "All ratios from one function in a named quadrant",
                        ),
                        SlotPlanRow(
                            "identity_prove",
                            "L2",
                            "Second identity proof — different formula",
                        ),
                        SlotPlanRow(
                            "standard_angle",
                            "L2",
                            "One-step standard-angle value only",
                            max_marks=3,
                        ),
                        SlotPlanRow(
                            "ratio_find",
                            "L3",
                            "Reciprocal ratios in another quadrant",
                        ),
                        SlotPlanRow(
                            "hots_trig",
                            "L4",
                            "Prove identity then find exact value",
                        ),
                        SlotPlanRow(
                            "quadrant_reduction",
                            "L3",
                            "Reduce negative/large radian angle — all steps",
                        ),
                        SlotPlanRow(
                            "radian_degree",
                            "L3",
                            "Large degree reduction with reciprocal",
                        ),
                        SlotPlanRow(
                            "hots_trig",
                            "L5",
                            "HOTS: balanced OR — both branches same difficulty",
                            max_marks=6,
                        ),
                    ),
                ),
            ),
            standard_exact_degree_step=15,
            forbid_minute_with_exact_surd=True,
            max_or_difficulty_ratio=2.0,
            prompt_bullets=(
                "Max period/reduction-only items per paper as in skill-family caps.",
                "Exact surd sin/cos: angles that are multiples of 15° after reduction — not minute measures.",
                "OR branches: same archetype and comparable effort on both paths.",
                "Include identity proof and ratio-from-one-function; avoid repeated reduction drills.",
            ),
            proof_route_rules=(
                ProofRouteRule(
                    r"sin\s*\(\s*π\s*/\s*2\s*[-−]\s*x",
                    "sin(a",
                    "cos(a",
                ),
            ),
            stem_pattern_caps=(
                StemPatternCap(
                    r"express\s+\d+°\s+in\s+radian.*quadrant.*sin.*cos",
                    1,
                ),
            ),
            critical_issue_tokens=_DEFAULT_CRITICAL_TOKENS,
            reject_flag_prefixes=_DEFAULT_REJECT_PREFIXES,
            max_marks_inflated_reject=2,
        ),
    )


_register_trigonometry()
