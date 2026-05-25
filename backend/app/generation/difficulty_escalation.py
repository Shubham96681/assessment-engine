"""
Difficulty escalation — RD Sharma / JEE-style prompts from ChapterRulePack.difficulty_escalation.

No chapter-specific logic here; register configs in chapter_quality_registry.py.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.chapter_rule_packs import (
    DifficultyEscalationConfig,
    get_chapter_rule_pack,
)


def escalation_config(chapter: str) -> Optional[DifficultyEscalationConfig]:
    pack = get_chapter_rule_pack(chapter)
    cfg = pack.difficulty_escalation
    return cfg if cfg and cfg.enabled else None


def escalation_prompt_block(chapter: str) -> str:
    cfg = escalation_config(chapter)
    if not cfg:
        return ""
    lines = [f"DIFFICULTY ESCALATION — {get_chapter_rule_pack(chapter).display_title}:"]
    for line in cfg.prompt_lines:
        lines.append(f"- {line}")
    if cfg.min_identity_proof_items:
        lines.append(
            f"- Include at least {cfg.min_identity_proof_items} identity proof item(s)."
        )
    if cfg.min_prove_hence_chains:
        lines.append(
            f"- Include at least {cfg.min_prove_hence_chains} prove-then-hence chain(s)."
        )
    if cfg.require_balanced_or:
        lines.append("- OR options must have balanced cognitive load.")
    return "\n".join(lines)


def validate_escalation_quality(
    questions: List[Dict[str, Any]],
    *,
    chapter: str,
) -> Tuple[bool, List[str]]:
    cfg = escalation_config(chapter)
    if not cfg:
        return True, []
    issues: List[str] = []
    prove_n = 0
    hence_n = 0
    prove_re = re.compile(cfg.prove_stem_pattern, re.I) if cfg.prove_stem_pattern else None
    hence_re = re.compile(cfg.hence_stem_pattern, re.I) if cfg.hence_stem_pattern else None
    ratio_re = (
        re.compile(cfg.ratio_find_stem_pattern, re.I)
        if cfg.ratio_find_stem_pattern
        else None
    )
    all_ratios_re = (
        re.compile(cfg.all_ratios_stem_pattern, re.I)
        if cfg.all_ratios_stem_pattern
        else None
    )
    for q in questions:
        stem = (q.get("content") or q.get("question") or "").lower()
        if prove_re and prove_re.search(stem):
            prove_n += 1
        if hence_re and hence_re.search(stem):
            hence_n += 1
        for phrase in cfg.forbid_trivial_quadrant:
            if phrase.lower() in stem and ratio_re and ratio_re.search(stem):
                if all_ratios_re and all_ratios_re.search(stem):
                    issues.append(f"trivial_quadrant_ratio:{phrase}")
    if prove_n < cfg.min_identity_proof_items:
        issues.append(
            f"too_few_proofs:{prove_n}<{cfg.min_identity_proof_items}"
        )
    if hence_n < cfg.min_prove_hence_chains:
        issues.append(
            f"too_few_hence_chains:{hence_n}<{cfg.min_prove_hence_chains}"
        )
    return (not issues, issues)
