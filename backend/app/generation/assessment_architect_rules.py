"""
Senior assessment architect rules — CBSE / JEE Main / JEE Advanced.

Source of truth for PromptBuilder, quality gates, and Cursor rag-response agent.
Generate one question at a time; verify before proceeding; refuse on repeated failure.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

ROLE_SYSTEM_PROMPT = """You are a senior mathematics assessment architect with 20+ years of experience creating CBSE Board, JEE Main, and JEE Advanced examination papers.

Your sole purpose is exam-ready papers with mathematical perfection, verified difficulty accuracy, zero duplication, and complete document integrity.

You NEVER compromise on quality. If a question fails any validation check, STOP and regenerate it. Do not proceed to the next question until the current one passes ALL checks.

ABSOLUTE PROHIBITIONS: blank questions; header garbage (yjd, dfyil, test 11); raw LaTeX (\\mathfrak, \\downarrow); mislabeled difficulty; over/under-marking; exact duplicates; broken Hence chains; definition verification tasks; forbidden angles; papers under 80 marks for 3 hours.

Output: plain text + Unicode math only (π, √, θ, ≤, ∈). NO raw LaTeX commands in stems or answers."""

ABSOLUTE_PROHIBITIONS_TABLE = """
ABSOLUTE PROHIBITIONS (instant rejection):
| Defect | Prevention |
| Blank questions | Generate ONE at a time; verify completeness |
| Header garbage | Subject: Mathematics | Class: [11/12] | Date: [DD MMM YYYY] |
| LaTeX corruption | Unicode math only; ban \\mathfrak, \\downarrow, raw \\commands |
| Mislabeled difficulty | Step-Count Difficulty Algorithm before every label |
| Over-marked easy | Cognitive Step Mark Formula (not position) |
| Duplicates | Skill Registry — no structural clone |
| Broken Hence | 3-gate validation; sin 2x proof ≠ Hence sin 75° |
| Trivial verify | NEVER verify sin²θ+cos²θ=1 or given definitions |
| Forbidden angles | Approved Angle List only |
| Short papers | 3 hours → minimum 80 marks |
"""

# ---------------------------------------------------------------------------
# Step-count difficulty algorithm
# ---------------------------------------------------------------------------

DIFFICULTY_STEP_WEIGHTS: Dict[str, int] = {
    "direct_recall": 1,
    "single_reduction": 2,
    "formula_substitution": 2,
    "algebraic_manipulation": 3,
    "multi_formula_chain": 3,
    "proof_derivation": 4,
    "pattern_recognition": 4,
    "non_routine_insight": 5,
    "generalization": 5,
    "optimization_analysis": 5,
    "domain_restriction_check": 2,
}

DIFFICULTY_LABEL_BANDS: Tuple[Tuple[str, int, int], ...] = (
    ("Easy", 1, 3),
    ("Moderate", 4, 6),
    ("Hard", 7, 10),
    ("Very Hard", 11, 14),
    ("Extreme", 15, 99),
)

DIFFICULTY_ALGORITHM_PROMPT = """
STEP-COUNT DIFFICULTY ALGORITHM (mandatory before ANY label):
DIFFICULTY SCORE = Σ(step_weights): direct_recall(1), single_reduction(2), formula_substitution(2),
algebraic_manipulation(3), multi_formula_chain(3), proof_derivation(4), pattern_recognition(4),
non_routine_insight(5), generalization(5), optimization_analysis(5), domain_restriction_check(2).

| Label | Score | Time | Failure rate |
| Easy | 1-3 | 3-5 min | 10-20% |
| Moderate | 4-6 | 6-10 min | 30-45% |
| Hard | 7-10 | 12-18 min | 50-70% |
| Very Hard | 11-14 | 20-30 min | 70-85% |
| Extreme | 15+ | 30-45 min | 85-95% |

If calculated score differs from intended label by more than 1 level → REGENERATE or downgrade label.
FORBIDDEN Hard labels: bare Find sin/cos N°; definition verify only; Pythagorean triple only in QII.
"""

# ---------------------------------------------------------------------------
# Cognitive step mark formula
# ---------------------------------------------------------------------------

MARK_PER_STEP: Dict[str, float] = {
    "recall_standard_value": 0.5,
    "periodicity_reduction": 1.0,
    "quadrant_sign_determination": 1.0,
    "exact_value_computation": 1.0,
    "formula_proof": 3.0,
    "algebraic_expansion": 1.5,
    "factorization": 1.5,
    "rationalization": 1.5,
    "compound_angle_application": 2.0,
    "double_triple_angle": 2.0,
    "general_solution_derivation": 2.0,
    "interval_solution_counting": 1.5,
    "summation_evaluation": 2.0,
    "comparison_analysis": 1.0,
    "verification_check": 1.0,
    "optimization_extreme": 3.0,
}

MARK_ALLOCATION_RULES = """
COGNITIVE STEP MARK FORMULA:
TOTAL MARKS = Σ(mark_per_step); round to nearest integer (0.5 rounds up).
MINIMUM per question: 2 marks | MAX standard: 6 marks | MAX extended: 8 marks (4+ parts: proof+application+extension).
Marks by step count — NOT by question position.
"""

MARK_MIN = 2
MARK_MAX_STANDARD = 6
MARK_MAX_EXTENDED = 8
PAPER_MIN_MARKS_3H = 80

# ---------------------------------------------------------------------------
# Skill category variance matrix (codes P-D … C-I)
# ---------------------------------------------------------------------------

SKILL_CATEGORIES: Tuple[Dict[str, Any], ...] = (
    {"code": "P-D", "name": "Periodicity (degrees)", "max": 1},
    {"code": "P-R", "name": "Periodicity (radians)", "max": 1},
    {"code": "C-P", "name": "Compound angle proof", "max": 1},
    {"code": "M-A", "name": "Multiple angle", "max": 1},
    {"code": "P-S", "name": "Pythagorean system", "max": 1},
    {"code": "I-P", "name": "Complex identity proof", "max": 2},
    {"code": "T-E", "name": "Trigonometric equation", "max": 2},
    {"code": "I-T", "name": "Inverse trigonometry", "max": 1},
    {"code": "T-P", "name": "Triangle properties", "max": 1},
    {"code": "O-E", "name": "Optimization/extreme", "max": 1},
    {"code": "S-S", "name": "Series/summation", "max": 1},
    {"code": "C-I", "name": "Conditional A+B+C=π", "max": 1},
)

# Legacy id A–L maps to codes (for existing blueprint strings)
LEGACY_ID_TO_CODE: Dict[str, str] = {
    "A": "P-D",
    "B": "P-R",
    "C": "C-P",
    "D": "M-A",
    "E": "P-S",
    "F": "I-P",
    "G": "T-E",
    "H": "I-T",
    "I": "T-P",
    "J": "O-E",
    "K": "S-S",
    "L": "C-I",
}

TRIG_SLOT_CATEGORY_PLAN_10: Tuple[str, ...] = (
    "C-P", "M-A", "T-E", "P-S", "I-P", "P-R", "O-E", "I-T", "C-I", "P-D"
)

PAPER_MANDATORY_MINIMUMS_10: Tuple[str, ...] = (
    "T-E",  # general solution
    "O-E",  # optimization
    "I-T",  # inverse trig
    "C-P",  # proof + Hence chain (also M-A or I-P acceptable)
)

VARIANCE_MATRIX_PROMPT = """
SKILL CATEGORY VARIANCE MATRIX — maintain registry; no category over max per paper.
Codes: P-D, P-R, C-P, M-A, P-S, I-P(2), T-E(2), I-T, T-P, O-E, S-S, C-I.

MANDATORY for 10-question trigonometry paper:
- ≥1 T-E with general solution + interval counting
- ≥1 O-E optimization / max-min
- ≥1 I-T inverse trigonometry
- ≥1 proof with 3+ part Hence chain (C-P, M-A, or I-P)
"""

# ---------------------------------------------------------------------------
# Hence chain (3-gate)
# ---------------------------------------------------------------------------

HENCE_CHAIN_RULES = """
HENCE CHAIN — 3-GATE VALIDATION:
GATE 1 REQUIRES PREVIOUS: student with only prior part result can start.
GATE 2 SUFFICIENT: completable with prior result + standard knowledge only.
GATE 3 PROGRESSION: Foundation → Application → Extension.

FORBIDDEN HENCE:
- Hence verify [definition] (circular)
- Hence find [same angle, different formula] (parallel)
- Hence prove [unrelated base identity]
- Hence find sin 75° after proving sin 2x = 2 sin x cos x (needs sin(A+B), not double angle)
"""

# ---------------------------------------------------------------------------
# Approved / forbidden angles
# ---------------------------------------------------------------------------

APPROVED_ANGLES_DEGREES: Tuple[int, ...] = (
    15, 18, 22, 30, 36, 45, 60, 75, 105, 120, 135, 150, 165, 195, 210, 225, 240, 255, 300, 330,
)

FORBIDDEN_ANGLE_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"\b7\.5°|\b7\.5\s*deg", "forbidden_half_angle_7_5"),
    (r"\b17\.5°", "forbidden_17_5"),
    (r"\b37\.5°|\b52\.5°|\b67\.5°|\b82\.5°|\b97\.5°|\b112\.5°|\b127\.5°|\b142\.5°|\b157\.5°", "forbidden_nested_half"),
    (r"162°\s*30|162\s*degrees?\s*30|162°30", "forbidden_minute_angle"),
    (r"\d+°\s*\d+['′]", "forbidden_degree_minute"),
)

ANGLE_SELECTION_RULES = """
APPROVED ANGLES (exact surd): 15°, 18°, 22.5°(π/8), 30°, 36°, 45°, 60°, 75°, 105°, 120°, 135°, 150°, 165°, 195°, 255°, 330°, π/12, π/6, π/4, π/3, π/2 multiples after reduction.

FORBIDDEN: 7.5°, 17.5°, 37.5°, 52.5°, 67.5°, 82.5°, 97.5°, 112.5°, 127.5°, 142.5°, 157.5°, 162°30′, any degree-minute notation.
"""

# ---------------------------------------------------------------------------
# Stem / output prohibitions
# ---------------------------------------------------------------------------

FORBIDDEN_HARD_STEM_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"\bfind\s+sin\s+\d+°\s*\.?\s*$", "bare_periodicity_find"),
    (r"\bfind\s+cos\s+\d+°\s*exactly", "bare_periodicity_find"),
    (r"\bverify\s+that\s+sin²", "definition_verify_only"),
    (r"\bverify\s+sin²θ\s*\+\s*cos²θ", "definition_verify_only"),
    (r"\bhence\s+verify\b", "hence_verify_definition"),
    (
        r"if\s+sin\s*θ\s*=\s*\d+/\d+.*quadrant\s+II.*find\s+cos\s*θ\s*\.?\s*$",
        "pythagorean_triple_only",
    ),
)

LATEX_FORBIDDEN_PATTERNS: Tuple[str, ...] = (
    r"\\mathfrak",
    r"\\downarrow",
    r"\\,\s*\\,",
    r"\\begin\{",
    r"\\frac\{",
)

HEADER_GARBAGE_PATTERNS: Tuple[str, ...] = (
    r"\byjd\b",
    r"\bdfyil\b",
    r"\btest\s*11\b",
)

SELF_VERIFICATION_CHECKLIST = """
SELF-VERIFICATION (all 12 before finalizing each item):
[ ] Completeness — all parts (i)(ii)(iii) filled
[ ] Difficulty score matches label within 1 level
[ ] Mark sum = step marks; 2≤marks≤6 (8 if extended)
[ ] Category within variance max; registry updated
[ ] Angles from approved list only
[ ] Every Hence passes 3-gate validation
[ ] Solution verified symbolically
[ ] No duplicate / structural clone
[ ] No definition verification
[ ] No LaTeX corruption — Unicode only
[ ] Header clean — exact template
[ ] JSON valid for rag_response (id, type, question, marks, correct_answer)
"""

GENERATION_WORKFLOW = """
GENERATION WORKFLOW:
STEP 1 Plan — 80 marks / 3h; 10-12 questions; assign categories from matrix; target difficulty each.
STEP 2 Per question — write stem → score difficulty → allocate marks → full solution → checklist → pass or regenerate.
STEP 3 Registry — record category code per slot; no duplicate over max.
STEP 4 Assembly — header template; sum marks; distribution; full paper checklist.
EMERGENCY STOP: 3 consecutive failures; <80% functional count; zero Hard+ for hard paper; corruption detected.
"""

ESCALATION_TEMPLATES = """
DIFFICULTY ESCALATION (if score too low for label):
Easy→Moderate: general solution Hence; parameter p; interval count.
Moderate→Hard: proof before compute; 2+ formula chain; sum solutions in [a,b]; quadrant trap.
Hard→VH: a³+b³ / nested surds; A+B+C=π pattern; prove intermediate identity first.
VH→Extreme: series; calculus-free optimization; Chebyshev roots (Class 12+ only).
"""

PAPER_HEADER_TEMPLATE = """INSTITUTION NAME — CBSE Board Pattern — Class {class_label} — Mathematics
Subject: Mathematics | Class: {class_label} | Date: {date}
Time: 3 Hours | Total Marks: {total_marks} | Total Questions: {question_count}
Difficulty Distribution: {difficulty_distribution}
GENERAL INSTRUCTIONS:
All questions are compulsory.
Show all working clearly. Marks awarded for method.
Calculators NOT permitted. Exact surd form unless stated otherwise.
Hence parts depend logically on previous parts."""

# ---------------------------------------------------------------------------
# Legacy aliases for imports
# ---------------------------------------------------------------------------

DIFFICULTY_VERIFICATION_PROTOCOL = DIFFICULTY_ALGORITHM_PROMPT
TRIG_VARIANCE_CATEGORIES = SKILL_CATEGORIES
STEP_MARK_WEIGHTS = {k: (v, v) for k, v in DIFFICULTY_STEP_WEIGHTS.items()}

ERROR_HANDLING_RULES = ESCALATION_TEMPLATES


def difficulty_label_from_score(score: int) -> str:
    for label, lo, hi in DIFFICULTY_LABEL_BANDS:
        if lo <= score <= hi:
            return label
    return "Extreme"


def compute_difficulty_score(stem: str, answer: str = "") -> int:
    """Heuristic cognitive step score from stem + model answer."""
    text = f"{stem} {answer}".lower()
    score = 0
    if re.search(r"\bprove\b", text):
        score += DIFFICULTY_STEP_WEIGHTS["proof_derivation"]
    if re.search(r"\bhence\b", text):
        score += 2
    if re.search(r"\(i\).*\(ii\).*\(iii\)", stem, re.I | re.S) or re.search(
        r"\(iii\)", stem, re.I
    ):
        score += 2
    if re.search(r"\bor\b", text):
        score += 1
    if re.search(r"\bgeneral\s+solution\b", text):
        score += DIFFICULTY_STEP_WEIGHTS["generalization"]
    if re.search(r"\bmax\b|\bmin\b|maximum|minimum", text):
        score += DIFFICULTY_STEP_WEIGHTS["optimization_analysis"]
    if re.search(r"tan\^?\{-1\}|sin\^?\{-1\}|arctan|arcsin|inverse", text):
        score += DIFFICULTY_STEP_WEIGHTS["multi_formula_chain"]
    if re.search(r"\bsolve\b.*\[.*,.*\]|\\bin\b|for\s+x\s*∈", text):
        score += DIFFICULTY_STEP_WEIGHTS["algebraic_manipulation"]
    if re.search(r"\bexpress\b.*radian|\breduce\b|principal angle", text):
        score += DIFFICULTY_STEP_WEIGHTS["single_reduction"]
    if re.search(r"\bfind\s+(?:sin|cos|tan)\s+\d+°?\s*\.?\s*$", stem.strip(), re.I):
        score += DIFFICULTY_STEP_WEIGHTS["direct_recall"]
    steps = len(re.findall(r"\bstep\s*\d+", answer, re.I))
    score += min(4, steps)
    return max(1, score)


def suggest_marks_from_answer(answer: str, *, cap: int = MARK_MAX_STANDARD) -> int:
    """Round cognitive step marks from answer structure."""
    if not answer:
        return 4
    total = 0.0
    low = answer.lower()
    if re.search(r"\bprove\b", low):
        total += MARK_PER_STEP["formula_proof"]
    if re.search(r"\bhence\b", low):
        total += MARK_PER_STEP["compound_angle_application"]
    total += len(re.findall(r"\bstep\s*\d+", answer, re.I)) * 1.0
    if re.search(r"\bgeneral\s+solution\b", low):
        total += MARK_PER_STEP["general_solution_derivation"]
    if re.search(r"\bmaximum\b|\bminimum\b|\bmax\b|\bmin\b", low):
        total += MARK_PER_STEP["optimization_extreme"]
    parts = len(re.findall(r"\([i]+\)", answer, re.I))
    total += max(0, parts - 1) * 1.0
    rounded = int(math.floor(total + 0.5))
    ext_cap = MARK_MAX_EXTENDED if parts >= 4 else cap
    return min(ext_cap, max(MARK_MIN, rounded))


def classify_skill_category(stem: str, archetype_id: str = "") -> str:
    """Assign variance-matrix code from stem heuristics."""
    low = (stem or "").lower()
    arch = (archetype_id or "").lower()
    if re.search(r"tan\^?\{-1\}|sin\^?\{-1\}|arctan|arcsin|inverse", low):
        return "I-T"
    if re.search(r"\bmax\b|\bminimum\b|\bmin\b.*\bsin|R sin", low):
        return "O-E"
    if re.search(r"\bsolve\b", low) and re.search(r"\[.*,.*\]|for\s+x\s*∈", low):
        return "T-E"
    if re.search(r"\ba\s*\+\s*b\s*\+\s*c\s*=\s*π|a+b+c=\\pi", low):
        return "C-I"
    if re.search(r"\bprove\b.*\bsin\s*\(\s*a\s*[\+\-]", low):
        return "C-P"
    if re.search(r"\bsin\s*2|cos\s*3|double angle|triple", low):
        return "M-A"
    if re.search(r"\bsec\b|\bcosec\b|\bcot\b", low) and re.search(r"\bfind\b.*\bquadrant", low):
        return "P-S"
    if re.search(r"\bprove\b.*\bidentity|\(1\s*\+\s*cos", low):
        return "I-P"
    if re.search(r"\bπ/|-\d+π/|\bradian\b", low) and re.search(r"\breduce\b|principal", low):
        return "P-R"
    if re.search(r"\b\d+°", low) and re.search(r"\bquadrant\b|radian measure", low):
        return "P-D"
    if "hots" in arch:
        return "T-E"
    if "ratio" in arch:
        return "P-S"
    if "identity" in arch:
        return "I-P"
    return "C-P"


def classify_forbidden_hard_stem(stem: str) -> List[str]:
    if not stem:
        return []
    low = stem.lower()
    tags: List[str] = []
    for pat, tag in FORBIDDEN_HARD_STEM_PATTERNS:
        if re.search(pat, low, re.I):
            tags.append(tag)
    if re.search(r"\bprove\b.*\bsin\s*2", low) and re.search(
        r"\bhence\b.*\bsin\s+75", low
    ):
        tags.append("hence_wrong_base_double_to_75")
    return tags


def classify_forbidden_angles(stem: str) -> List[str]:
    tags: List[str] = []
    for pat, tag in FORBIDDEN_ANGLE_PATTERNS:
        if re.search(pat, stem, re.I):
            tags.append(tag)
    return tags


def detect_latex_corruption(text: str) -> List[str]:
    flags: List[str] = []
    for pat in LATEX_FORBIDDEN_PATTERNS:
        if re.search(pat, text):
            flags.append(f"latex_corruption:{pat}")
    return flags


def validate_hence_chain_stem(stem: str) -> List[str]:
    low = (stem or "").lower()
    flags: List[str] = []
    if re.search(r"\bhence\s+verify\b", low):
        flags.append("hence_verify_definition")
    if re.search(r"\bhence\s+find\s+sin\s+\d+°", low) and re.search(
        r"\bprove\b.*\bsin\s*2", low
    ):
        flags.append("hence_sin2x_to_sin75")
    if re.search(r"\bhence\s+find\s+sin\s+75", low) and re.search(
        r"\bprove\b.*\bsin\s*2\s*x\s*=\s*2", low
    ):
        flags.append("hence_sin2x_to_sin75")
    return flags


def variance_matrix_prompt_block(
    chapter: str,
    question_count: int = 10,
) -> str:
    ch = (chapter or "").strip().lower()
    if ch != "trigonometry":
        return (
            "SKILL VARIANCE: spread categories; no structural clones; "
            f"minimum {PAPER_MIN_MARKS_3H} marks for 3-hour paper."
        )
    plan = list(TRIG_SLOT_CATEGORY_PLAN_10[:question_count])
    while len(plan) < question_count:
        plan.append(SKILL_CATEGORIES[len(plan) % len(SKILL_CATEGORIES)]["code"])
    lines = [VARIANCE_MATRIX_PROMPT.strip(), "- Slot → category plan:"]
    for cat in SKILL_CATEGORIES:
        lines.append(f"  [{cat['code']}] {cat['name']} (max {cat['max']}/paper)")
    for i, code in enumerate(plan[:question_count], 1):
        lines.append(f'  id "{i}": category {code}')
    lines.append(
        f"- Mandatory minimums (10Q): {', '.join(PAPER_MANDATORY_MINIMUMS_10)}"
    )
    return "\n".join(lines)


def architect_rules_block(*, full_hard: bool = False) -> str:
    parts = [
        ROLE_SYSTEM_PROMPT,
        ABSOLUTE_PROHIBITIONS_TABLE.strip(),
        DIFFICULTY_ALGORITHM_PROMPT.strip(),
        MARK_ALLOCATION_RULES.strip(),
        HENCE_CHAIN_RULES.strip(),
        ANGLE_SELECTION_RULES.strip(),
        SELF_VERIFICATION_CHECKLIST.strip(),
        GENERATION_WORKFLOW.strip(),
        ESCALATION_TEMPLATES.strip(),
    ]
    if full_hard:
        parts.append(
            "FULL HARD UI: every item scores ≥7 (Hard) or label Moderate only with 4+ parts; "
            "minimum 80 marks paper; ban bare Find sin/cos/tan X°."
        )
    return "\n\n".join(parts)


def evaluate_architect_compliance(
    q: Dict[str, Any],
    *,
    full_hard: bool = False,
    locked_chapter: str = "",
    ui_difficulty: str = "medium",
    target_label: str = "",
) -> Dict[str, Any]:
    stem = (q.get("content") or q.get("question") or "").strip()
    answer = (q.get("correct_answer") or q.get("answer") or "")
    ui = (ui_difficulty or "").lower()
    flags: List[str] = []
    score_f = 1.0

    forbidden = classify_forbidden_hard_stem(stem)
    for tag in forbidden:
        flags.append(f"architect_forbidden:{tag}")
        score_f -= 0.35

    for tag in classify_forbidden_angles(stem):
        flags.append(f"architect_forbidden_angle:{tag}")
        score_f -= 0.4

    for hf in validate_hence_chain_stem(stem):
        flags.append(f"architect_{hf}")
        score_f -= 0.25

    for lf in detect_latex_corruption(stem + answer):
        flags.append(f"architect_{lf}")
        score_f -= 0.5

    diff_score = compute_difficulty_score(stem, answer)
    computed_label = difficulty_label_from_score(diff_score)
    q["architect_difficulty_score"] = diff_score
    q["architect_difficulty_label"] = computed_label

    if ui in ("hard", "difficult") or full_hard:
        if diff_score < 7:
            flags.append(f"architect_underlabeled_hard:score={diff_score}_label={computed_label}")
            score_f -= 0.4
        if len(stem.split()) < 20 and not re.search(r"\(i\)|\(ii\)", stem, re.I):
            flags.append("architect_stem_too_thin")
            score_f -= 0.3

    marks = int(q.get("marks") or 0)
    suggested = suggest_marks_from_answer(answer)
    if marks > MARK_MAX_EXTENDED:
        flags.append("architect_marks_exceed_cap")
        score_f -= 0.3
    elif marks >= 5 and diff_score <= 3:
        flags.append("architect_overmarked_easy")
        score_f -= 0.35
    elif marks < MARK_MIN:
        flags.append("architect_under_minimum_marks")
        score_f -= 0.2

    if target_label and computed_label:
        bands = {b[0]: (b[1], b[2]) for b in DIFFICULTY_LABEL_BANDS}
        tgt = target_label.replace("_", " ").title()
        if tgt in bands and computed_label in bands:
            if abs(bands[computed_label][0] - bands[tgt][0]) > 4:
                flags.append("architect_label_score_mismatch")

    ok = score_f >= (0.65 if full_hard else 0.5) and not any(
        f.startswith("architect_forbidden:") for f in flags
    )
    return {
        "architect_ok": ok,
        "architect_score": round(max(0.0, min(1.0, score_f)), 3),
        "architect_flags": flags,
        "architect_difficulty_score": diff_score,
        "architect_difficulty_label": computed_label,
        "architect_suggested_marks": suggested,
        "skill_category": classify_skill_category(stem, q.get("archetype_id", "")),
    }


def validate_paper_architect(
    questions: Sequence[Dict[str, Any]],
    *,
    expected_count: int = 10,
    full_hard: bool = False,
    locked_chapter: str = "trigonometry",
) -> Dict[str, Any]:
    """Paper-level architect validation."""
    flags: List[str] = []
    total_marks = sum(float(q.get("marks") or 0) for q in questions)
    if total_marks < PAPER_MIN_MARKS_3H and expected_count >= 8:
        flags.append(f"paper_under_80_marks:{int(total_marks)}")

    codes: List[str] = []
    for q in questions:
        stem = q.get("content") or q.get("question") or ""
        codes.append(
            q.get("skill_category")
            or classify_skill_category(stem, q.get("archetype_id", ""))
        )

    from collections import Counter

    counts = Counter(codes)
    max_map = {c["code"]: c["max"] for c in SKILL_CATEGORIES}
    for code, n in counts.items():
        if code in max_map and n > max_map[code]:
            flags.append(f"category_over_max:{code}={n}")

    if locked_chapter == "trigonometry" and expected_count >= 10:
        present = set(codes)
        if "T-E" not in present:
            flags.append("missing_mandatory:T-E_general_solution")
        if "O-E" not in present:
            flags.append("missing_mandatory:O-E_optimization")
        if "I-T" not in present:
            flags.append("missing_mandatory:I-T_inverse")
        if not present.intersection({"C-P", "M-A", "I-P"}):
            flags.append("missing_mandatory:proof_hence_chain")

    if full_hard:
        hard_count = sum(
            1
            for q in questions
            if compute_difficulty_score(
                q.get("content") or q.get("question") or "",
                q.get("correct_answer") or "",
            )
            >= 7
        )
        if hard_count < max(1, expected_count // 2):
            flags.append(f"full_hard_insufficient_deep_items:{hard_count}")

    return {
        "paper_architect_ok": len(flags) == 0,
        "paper_architect_flags": flags,
        "total_marks": total_marks,
        "category_counts": dict(counts),
    }


def should_reject_architect_violation(
    q: Dict[str, Any],
    *,
    full_hard: bool = False,
    locked_chapter: str = "",
    ui_difficulty: str = "medium",
) -> bool:
    ui = (ui_difficulty or "").lower()
    if ui not in ("hard", "difficult") and not full_hard:
        return False
    report = evaluate_architect_compliance(
        q, full_hard=full_hard, locked_chapter=locked_chapter, ui_difficulty=ui
    )
    q.update({k: v for k, v in report.items() if k.startswith("architect_")})
    if not report.get("architect_ok"):
        return True
    critical = (
        "architect_forbidden:",
        "architect_forbidden_angle:",
        "hence_verify",
        "hence_sin2x",
        "latex_corruption",
        "architect_underlabeled_hard",
        "architect_overmarked_easy",
    )
    return any(any(c in f for c in critical) for f in report.get("architect_flags") or [])
