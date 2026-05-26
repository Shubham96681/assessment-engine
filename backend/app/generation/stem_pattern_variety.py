"""
Per-slot stem layout patterns — avoid every question using (i)(ii)(iii).

Human textbooks mix: single prove, direct find, (i)(ii) only, full triple parts, OR, sparse stems.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Pattern ids used in prompts and validation
PATTERN_PROVE_HENCE_III = "prove_hence_iii"
PATTERN_PROVE_HENCE_II = "prove_hence_ii"
PATTERN_PROVE_ONLY = "prove_only"
PATTERN_DIRECT_FIND = "direct_find"
PATTERN_RATIO_FIND = "ratio_find_single"
PATTERN_EQUATION_SOLVE = "equation_solve"
PATTERN_BALANCED_OR = "balanced_or"
PATTERN_SPARSE_SINGLE = "sparse_single"
PATTERN_INLINE_HENCE = "inline_hence_single"

_PATTERN_HINTS: Dict[str, str] = {
    PATTERN_PROVE_HENCE_III: "Use (i)(ii)(iii): prove → apply → numeric Hence.",
    PATTERN_PROVE_HENCE_II: "Use (i)(ii) only: prove identity → Hence numeric (no part iii).",
    PATTERN_PROVE_ONLY: "Single stem — prove one identity; no (i)(ii) labels.",
    PATTERN_DIRECT_FIND: "Single stem — all givens in one sentence; find one quantity (no sub-parts).",
    PATTERN_RATIO_FIND: "Single stem — one ratio given in a named quadrant; find remaining ratios.",
    PATTERN_EQUATION_SOLVE: "Solve in interval; optional (i) factor (ii) list solutions — max two parts.",
    PATTERN_BALANCED_OR: "Balanced OR — two branches, each multi-step; no (i)(ii)(iii) wrapper.",
    PATTERN_SPARSE_SINGLE: "Minimal stem (12–22 words); deep answer only — no sub-part labels.",
    PATTERN_INLINE_HENCE: "One stem with prove then 'Hence find …' inline — no (i)(ii)(iii).",
}

# Default 10-slot trigonometry full-hard rotation (≤40% triple-part)
TRIGONOMETRY_FULL_HARD_PATTERNS: Tuple[str, ...] = (
    PATTERN_PROVE_HENCE_II,
    PATTERN_PROVE_ONLY,
    PATTERN_EQUATION_SOLVE,
    PATTERN_DIRECT_FIND,
    PATTERN_SPARSE_SINGLE,
    PATTERN_RATIO_FIND,
    PATTERN_PROVE_HENCE_III,
    PATTERN_INLINE_HENCE,
    PATTERN_PROVE_HENCE_III,
    PATTERN_BALANCED_OR,
)

_SUBPART_RE = re.compile(r"\([ivx]+\)", re.I)


def pattern_requires_subparts(pattern_id: str) -> bool:
    return pattern_id in (
        PATTERN_PROVE_HENCE_III,
        PATTERN_PROVE_HENCE_II,
        PATTERN_EQUATION_SOLVE,
        PATTERN_BALANCED_OR,
    )


def pattern_requires_triple_subparts(pattern_id: str) -> bool:
    return pattern_id == PATTERN_PROVE_HENCE_III


def pattern_hint(pattern_id: str) -> str:
    return _PATTERN_HINTS.get(pattern_id, pattern_id)


def pattern_forbids_subparts(pattern_id: str) -> bool:
    return pattern_id in (
        PATTERN_PROVE_ONLY,
        PATTERN_DIRECT_FIND,
        PATTERN_RATIO_FIND,
        PATTERN_SPARSE_SINGLE,
        PATTERN_INLINE_HENCE,
    )


def assign_stem_patterns(
    question_count: int,
    *,
    chapter: str = "generic",
    full_hard: bool = False,
) -> List[str]:
    """Return stem_format id per slot (1..N)."""
    ch = (chapter or "").strip().lower()
    if full_hard and ch == "trigonometry":
        base = list(TRIGONOMETRY_FULL_HARD_PATTERNS)
        out: List[str] = []
        for i in range(question_count):
            out.append(base[i % len(base)])
        return out
  # Board / medium: uneven — about half without triple parts
    rotation = (
        PATTERN_DIRECT_FIND,
        PATTERN_PROVE_HENCE_II,
        PATTERN_PROVE_ONLY,
        PATTERN_RATIO_FIND,
        PATTERN_INLINE_HENCE,
        PATTERN_PROVE_HENCE_III,
        PATTERN_EQUATION_SOLVE,
        PATTERN_SPARSE_SINGLE,
        PATTERN_PROVE_HENCE_II,
        PATTERN_DIRECT_FIND,
    )
    return [rotation[i % len(rotation)] for i in range(question_count)]


def stem_pattern_prompt_block(
    patterns: Sequence[str],
    *,
    roles: Optional[Sequence[str]] = None,
) -> str:
    lines = [
        "STEM PATTERN VARIETY (mandatory — do NOT use (i)(ii)(iii) on every question):",
        "- At most 40% of slots may use three labeled sub-parts (i)(ii)(iii).",
        "- Rotate layouts slot by slot; match the pattern id for each id.",
        "",
    ]
    for i, pid in enumerate(patterns):
        slot = i + 1
        role = ""
        if roles and i < len(roles):
            role = f" | {roles[i]}"
        hint = _PATTERN_HINTS.get(pid, pid)
        lines.append(f'  id "{slot}": pattern={pid}{role} — {hint}')
    lines.append("")
    lines.append(
        "- BAN: copying the same (i)(ii)(iii) prove→Hence skeleton on more than 4 slots per paper."
    )
    return "\n".join(lines)


def count_subparts(text: str) -> int:
    return len(_SUBPART_RE.findall(text or ""))


def validate_question_stem_pattern(
    content: str,
    pattern_id: str,
) -> Tuple[bool, List[str]]:
    """Check stem matches assigned pattern."""
    flags: List[str] = []
    n = count_subparts(content)
    if pattern_forbids_subparts(pattern_id) and n > 0:
        flags.append("unexpected_subparts")
    if pattern_id == PATTERN_PROVE_HENCE_III and n < 3:
        flags.append("missing_iii_parts")
    if pattern_id == PATTERN_PROVE_HENCE_II and n not in (2,):
        if n >= 3:
            flags.append("too_many_subparts_for_ii_pattern")
        elif n < 2:
            flags.append("missing_ii_parts")
    if pattern_id == PATTERN_BALANCED_OR and " OR " not in content.upper():
        flags.append("missing_or_branch")
    if pattern_id == PATTERN_EQUATION_SOLVE and "solve" not in content.lower():
        flags.append("missing_solve_verb")
    ok = len(flags) == 0
    return ok, flags


def validate_paper_stem_variety(
    questions: Sequence[Dict[str, Any]],
    *,
    slot_patterns: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Reject papers where every stem looks identical."""
    flags: List[str] = []
    triple = 0
    with_sub = 0
    for i, q in enumerate(questions):
        content = (q.get("content") or "").strip()
        n = count_subparts(content)
        if n >= 3:
            triple += 1
        if n >= 1:
            with_sub += 1
        pid = None
        if slot_patterns and i < len(slot_patterns):
            pid = slot_patterns[i]
        elif q.get("stem_format"):
            pid = q["stem_format"]
        if pid:
            ok, pflags = validate_question_stem_pattern(content, pid)
            if not ok:
                flags.append(f"Q{i + 1}:{','.join(pflags)}")
    n_q = len(questions) or 1
    if triple > max(2, int(0.45 * n_q)):
        flags.append("too_many_triple_subpart_stems")
    if with_sub == n_q and n_q >= 5:
        flags.append("all_questions_have_subparts")
    return {
        "stem_variety_ok": len(flags) == 0,
        "stem_variety_flags": flags,
        "triple_subpart_count": triple,
        "subpart_stem_count": with_sub,
    }
