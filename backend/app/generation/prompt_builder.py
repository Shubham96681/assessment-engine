"""
PromptBuilder — source-calibrated prompts for CBSE / RD Sharma assessment generation.

Mirrors the phyEngine pattern: difficulty guide (1–9), few-shot corpus style,
topic scope, retrieval context, and structured output contract.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.generation.assessment_architect_rules import (
    ROLE_SYSTEM_PROMPT,
    architect_rules_block,
    variance_matrix_prompt_block,
)
from app.generation.semantic_generation_plan import SemanticGenerationPlan


class PromptBuilder:
    """Construct prompts with board/JEE-style difficulty calibration and corpus references."""

    DIFFICULTY_GUIDE = """
DIFFICULTY CALIBRATION (use reference sources for style and complexity — invent new stems):

Level 1–2 (Board easy / NCERT drill):
- Single skill, 1–2 steps, clean integers or standard angles (30°, 45°, 60°)
- Example: Express 60° in radians; find sin 30°
- Reference: NCERT exemplar, Class 10 Section A compression

Level 3–4 (Board medium / RD Sharma core):
- Two sub-parts (i)(ii), combine identity + numeric Hence OR ratio find in named quadrant
- Example: Prove sin(A+B); Hence find sin 75°; all ratios from cos θ in QII
- Reference: RD Sharma exercise depth, CBSE SQP 3–4 mark items

Level 5–6 (Board hard / RS Aggarwal challenge):
- Prove + Hence chain, hidden givens (sin θ + cos θ), 4+ answer steps
- Multi-concept fusion without minute angles; exact surds after 15° reduction
- Reference: RS Aggarwal higher exercise, CBSE case-study style

Level 7–8 (Full hard / JEE Main trigonometry — Class 10–11 board stretch):
- (i)(ii)(iii) mandatory; balanced OR on capstone slot; 5+ theorem links in answer
- Equation in interval, tan-sum identities, A+B+C=π chains
- Reference: Advanced trigonometry benchmark (6 marks/item), JEE Main compound-angle papers

Level 9 (Hardest bounded — full_hard capstone):
- Novel labels and numbers only; same depth as Level 7–8 but zero one-step recall
- Self-contained; one unambiguous exact surd or rational final answer per branch
- BAN: bare "Find cos X°"; duplicate reduction templates; fusion graph copies
"""

    FEW_SHOT_TRIGONOMETRY = """
EXAMPLE STYLES — TRIGONOMETRY (do not copy stems):

=== BOARD L4 (prove + Hence, ~4 marks) ===
"(i) Prove that cos(A − B) = cos A cos B + sin A sin B. (ii) Hence find cos 15° in exact surd form."
Answer: Unit-circle / addition identity proof → cos(45°−30°) → (√6+√2)/4.

=== BOARD L5 (fusion, ~6 marks) ===
"(i) Prove sin 2θ = 2 sin θ cos θ. (ii) If sin η = 4/5, η in quadrant III, find cos η. (iii) Hence find cos 2η."
Answer: Identity proof → ratio signs → double-angle numeric.

=== FULL HARD (equation + interval) ===
"Solve 2 cos²x − cos x − 1 = 0 for x ∈ [0, 2π). (i) Factor. (ii) List solutions. (iii) Count distinct solutions."
Answer: (2 cos x + 1)(cos x − 1) = 0 with quadrant-aware root list.
"""

    FEW_SHOT_CIRCLES = """
EXAMPLE STYLES — CIRCLES (do not copy stems):

=== BOARD L4 (tangent length) ===
"PA and PB are tangents from P to a circle with centre O, radius 5 cm. If OP = 13 cm, find PA."
Answer: Right triangle OTP with TA² = OP² − r².

=== BOARD L5 (prove + Hence) ===
"Prove that tangents drawn from an external point to a circle are equal. Hence find length of tangent when r = 7 cm and distance from P to O is 25 cm."
"""

    FEW_SHOT_QUADRATIC = """
EXAMPLE STYLES — QUADRATIC (do not copy stems):

=== BOARD L3 (roots) ===
"Find the roots of x² − 5x + 6 = 0 and verify the relation between roots and coefficients."

=== BOARD L5 (parameter) ===
"For what value of k does 2x² + kx + 8 = 0 have equal roots? Hence find the common root."
"""

    FEW_SHOT_GENERIC = """
EXAMPLE STYLES — TEXTBOOK (generic chapter):
- Compressed stem with numeric givens first
- Model answer: Given → Step 1 → Step 2 → Hence
- Theorems named only in answers, never in stems
"""

    CHAPTER_FEW_SHOTS: Dict[str, str] = {
        "trigonometry": FEW_SHOT_TRIGONOMETRY,
        "circles": FEW_SHOT_CIRCLES,
        "quadratic": FEW_SHOT_QUADRATIC,
        "generic": FEW_SHOT_GENERIC,
    }

    SYSTEM_PROMPT = ROLE_SYSTEM_PROMPT + """

Generate NOVEL questions — never copy existing stems from the corpus. Match style, compression, and step depth of reference excerpts only.

OUTPUT FORMAT (valid JSON array for file-agent mode):
[
  {
    "id": "1",
    "type": "LongAnswer|ShortAnswer|MCQ|FigureBased",
    "question": "Stem with (i)(ii) sub-parts when required",
    "marks": 4,
    "correct_answer": "Given → Step 1 → Step 2 → Hence (theorems only here)",
    "explanation": "Marking scheme value points",
    "theorem_tags": ["optional"],
    "cognitive_type": "proof|computation|fusion"
  }
]

CRITICAL GUIDELINES:
- Match the calibrated difficulty level (1–9) and slot band (L1–L5) in the plan
- Level ≥5: multi-step reasoning, prove+Hence or balanced OR
- Level ≥7: ban one-step recall; require (i)(ii)(iii) or OR branches of equal effort
- Stems self-contained; exact surds for standard angles (multiples of 15° after reduction)
- For MCQ: four options with plausible wrong intermediates
- For FigureBased: figure_spec only when necessary; max count per paper plan
- Do not output solution-only text; every object needs a complete question stem
- Marks = sum of cognitive step types (max 6; 8 only for 4+ part capstone)
- Verify difficulty label against step count before labeling hard / very hard"""

    @classmethod
    def architect_section(
        cls,
        *,
        chapter: str = "generic",
        question_count: int = 10,
        full_hard: bool = False,
    ) -> str:
        """Assessment architect protocol — difficulty, marks, variance, Hence, angles."""
        parts = [
            "ASSESSMENT ARCHITECT PROTOCOL (mandatory):",
            architect_rules_block(full_hard=full_hard),
            variance_matrix_prompt_block(chapter, question_count),
        ]
        return "\n\n".join(parts)

    @classmethod
    def ui_difficulty_to_level(
        cls,
        difficulty: str,
        *,
        full_hard: bool = False,
        slot_band: str = "L3",
    ) -> int:
        """Map UI difficulty + slot band to 1–9 calibration level."""
        if full_hard:
            return 9 if slot_band.upper() == "L5" else 8
        d = (difficulty or "medium").lower()
        band = (slot_band or "L3").upper()
        if d in ("hard", "difficult"):
            return 7 if band in ("L4", "L5") else 6
        if d == "easy":
            return 2 if band in ("L1", "L2") else 3
        if band == "L5":
            return 6
        if band == "L4":
            return 5
        return 4

    @classmethod
    def difficulty_section(cls, plan: SemanticGenerationPlan) -> str:
        """Full difficulty block for prompt assembly."""
        from app.generation.difficulty_regime import regime_calibration_lines
        from app.generation.full_hard_mode import is_full_hard_paper

        p = plan
        regime = getattr(p, "difficulty_regime", "") or "board_medium"
        fh = getattr(p, "full_hard", False)
        label = f"{p.difficulty.upper()} ({regime})"
        if fh:
            label = f"{p.difficulty.upper()} — FULL HARD PAPER ({regime})"

        peak_band = "L3"
        if p.slots:
            peak_band = max((s.band for s in p.slots), key=lambda b: b.upper())
        level = cls.ui_difficulty_to_level(
            p.difficulty, full_hard=fh, slot_band=peak_band
        )

        lines = [
            f"DIFFICULTY CALIBRATION: {label}.",
            f"TARGET LEVEL: {level}/9 (peak slot band {peak_band}).",
            cls.DIFFICULTY_GUIDE.strip(),
        ]
        lines.extend(f"  • {ln}" for ln in regime_calibration_lines(regime, p.locked_chapter))
        if fh:
            from app.generation.trigonometry_hard_benchmark import (
                benchmark_calibration_lines,
                benchmark_prompt_block,
            )

            if p.locked_chapter == "trigonometry":
                lines.extend(f"  • {ln}" for ln in benchmark_calibration_lines())
                lines.append(benchmark_prompt_block())
            else:
                lines.append(
                    "  • FULL HARD: every slot L5; 5+ steps; prove+Hence or balanced OR."
                )
        elif p.difficulty in ("hard", "difficult"):
            for pat in p.rule_pack.hard_difficulty_patterns[:4]:
                lines.append(f"  • {pat}")
        elif regime == "board_medium":
            lines.append("  • Standard mix: ~2 easy, ~2 medium, ~1 challenge.")
        return "\n".join(lines)

    @classmethod
    def few_shot_section(cls, chapter: str, *, full_hard: bool = False) -> str:
        ch = (chapter or "generic").strip().lower()
        block = cls.CHAPTER_FEW_SHOTS.get(ch, cls.FEW_SHOT_GENERIC)
        header = "FEW-SHOT STYLE (chapter-scoped; do not copy verbatim):"
        if full_hard and ch == "trigonometry":
            header += "\n[Full-hard benchmark: 6 marks/item; section A–F spread; OR on last slot.]"
        return f"{header}\n{block.strip()}"

    @classmethod
    def topic_scope_block(cls, plan: SemanticGenerationPlan) -> str:
        lines = [
            "STRICT TOPIC SCOPE:",
            f"- Locked chapter: {plan.chapter_title} (key={plan.locked_chapter})",
            f"- Subject: {plan.subject} | Class: {plan.class_label} | Track: {plan.exam_track}",
            f"- Questions: {plan.question_count} | Bloom: {plan.bloom_level}",
        ]
        if plan.topic_focus:
            lines.append(f"- Topic focus: {plan.topic_focus}")
        if plan.forbidden_terms:
            lines.append(
                "- Forbidden in stems/answers: "
                + ", ".join(plan.forbidden_terms[:12])
            )
        lines.extend(
            [
                "- Use ONLY structures from SOURCE and chapter rules below.",
                "- Invent new numbers, labels, and proof routes every generation.",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _format_context(
        cls,
        context_excerpt: str,
        *,
        chapter: str,
        retrieval_confidence: float = 0.0,
        retrieval_mode: str = "curriculum_fallback",
        ppo_exemplars: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        parts = [cls.few_shot_section(chapter)]

        if ppo_exemplars:
            ex_lines = ["HIGH-QUALITY PAST GENERATIONS (learn from reward, do not copy):"]
            for i, ex in enumerate(ppo_exemplars[:3], 1):
                q = ex.get("question", ex)
                if isinstance(q, dict):
                    q_text = str(q.get("question", q.get("content", "")))[:300]
                    a_text = str(q.get("correct_answer", q.get("answer", "")))[:150]
                    d_val = q.get("difficulty", "?")
                else:
                    q_text = str(q)[:300]
                    a_text = ""
                    d_val = "?"
                r = ex.get("reward", 0)
                ex_lines.append(
                    f"  --- Example {i} (reward: {r:.2f}, difficulty: {d_val}) ---\n"
                    f"  Question: {q_text}\n"
                    + (f"  Answer: {a_text}\n" if a_text else "")
                )
            parts.append("\n".join(ex_lines))

        if retrieval_mode == "curriculum_fallback":
            guidance = (
                "RAG STYLE: curriculum structures only; textbook-aligned.\n"
                "Avoid theorem fusion absent from syllabus list."
            )
        elif retrieval_mode == "pdf_rich":
            guidance = (
                f"RAG STYLE: match SOURCE compression and step depth "
                f"(confidence {retrieval_confidence:.2f}); new numbers/labels only."
            )
        else:
            guidance = "RAG STYLE: light SOURCE inspiration; prefer chapter rule pack structures."

        ctx = (context_excerpt or "").strip()
        if ctx:
            parts.append(
                f"{guidance}\n\nSOURCE CONTENT:\n---\n{ctx[:12000]}\n---"
            )
        else:
            parts.append(guidance)
        return "\n\n".join(parts)

    @classmethod
    def build_from_plan(
        cls,
        plan: SemanticGenerationPlan,
        *,
        type_tail: str = "",
        include_system: bool = False,
    ) -> Tuple[str, str]:
        """
        Build (system_prompt, user_prompt) from a semantic plan.

        When include_system is False, returns a single merged user prompt as ("", merged).
        """
        user_parts = [
            cls.topic_scope_block(plan),
            cls.difficulty_section(plan),
            cls.architect_section(
                chapter=plan.locked_chapter,
                question_count=plan.question_count,
                full_hard=getattr(plan, "full_hard", False),
            ),
            plan.rule_pack.preferred_types_block(),
        ]
        if plan.instructions:
            user_parts.append(f"Special instructions: {plan.instructions}")
        user_parts.append(cls._format_context(
            plan.context_excerpt,
            chapter=plan.locked_chapter,
            retrieval_confidence=plan.retrieval_confidence,
            retrieval_mode=plan.retrieval_mode,
        ))
        user = "\n\n".join(user_parts)
        if include_system:
            return cls.SYSTEM_PROMPT, user + (f"\n\n{type_tail}" if type_tail else "")
        return "", user + (f"\n\n{type_tail}" if type_tail else "")

    @classmethod
    def build_generation_prompt(
        cls,
        topic: str,
        difficulty: int,
        retrieved_context: List[Dict[str, Any]],
        *,
        chapter: str = "generic",
        question_type: str = "LongAnswer",
        count: int = 1,
        class_label: str = "10",
        subject: str = "Mathematics",
        full_hard: bool = False,
        topic_profile: Optional[Dict[str, Any]] = None,
        ppo_exemplars: Optional[List[Dict[str, Any]]] = None,
        sympy_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Standalone builder (phyEngine-style API) for scripts and local LLM paths.
        """
        context_str = cls._format_retrieved_list(
            retrieved_context,
            chapter=chapter,
            ppo_exemplars=ppo_exemplars,
        )
        sympy_str = cls._format_sympy(sympy_data)
        scope = cls._format_topic_profile(topic_profile, topic, chapter)

        ui = "hard" if difficulty >= 6 else ("easy" if difficulty <= 2 else "medium")
        diff_guide = cls.DIFFICULTY_GUIDE
        if full_hard:
            diff_guide += "\n[Mode: FULL HARD — target level 8–9/9 on every item.]"

        architect = cls.architect_section(
            chapter=chapter,
            question_count=count,
            full_hard=full_hard,
        )

        user_prompt = f"""Generate {count} mathematics question(s):

TOPIC / CHAPTER: {topic} (key={chapter})
DIFFICULTY: {difficulty}/9
UI TIER: {ui}
TYPE: {question_type}
CLASS: {class_label} | SUBJECT: {subject}

{scope}

{diff_guide}

{architect}

REFERENCE CORPUS (style and depth only — novel stems):
{context_str}

{sympy_str}

Generate {count} NOVEL question(s) at difficulty {difficulty}/9. Output valid JSON array."""

        return cls.SYSTEM_PROMPT, user_prompt

    @classmethod
    def _format_retrieved_list(
        cls,
        context: List[Dict[str, Any]],
        *,
        chapter: str,
        ppo_exemplars: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        parts = [cls.few_shot_section(chapter)]
        if ppo_exemplars:
            for i, ex in enumerate(ppo_exemplars[:3], 1):
                q = ex.get("question", ex)
                stem = (
                    q.get("question", q.get("content", ""))
                    if isinstance(q, dict)
                    else str(q)
                )
                parts.append(f"--- Past example {i} ---\n{str(stem)[:400]}\n")
        if context:
            rags = []
            for i, c in enumerate(context, 1):
                source = c.get("source", c.get("filename", "unknown"))
                text = str(c.get("text", c.get("content", "")))[:500]
                score = float(c.get("score", 0) or 0)
                rags.append(
                    f"--- Reference {i} [{source}, relevance {score:.2f}] ---\n{text}\n"
                )
            parts.append(
                "MATCHED CORPUS EXCERPTS:\n" + "\n".join(rags)
            )
        return "\n".join(parts)

    @classmethod
    def _format_topic_profile(
        cls,
        topic_profile: Optional[Dict[str, Any]],
        topic: str,
        chapter: str,
    ) -> str:
        if not topic_profile:
            return (
                f"STRICT TOPIC SCOPE:\n"
                f"- Chapter key: {chapter}\n"
                f"- Topic label: {topic}\n"
            )
        focus = topic_profile.get("focus_terms", [])[:14]
        avoid = topic_profile.get("avoid_terms", [])[:12]
        lines = [
            "STRICT TOPIC SCOPE:",
            f"- Requested: {topic_profile.get('requested', topic)}",
            f"- Resolved chapter: {topic_profile.get('topic', chapter)}",
        ]
        if topic_profile.get("subtopic"):
            lines.append(f"- Subtopic: {topic_profile['subtopic']}")
        if focus:
            lines.append("- Must center on: " + ", ".join(str(t) for t in focus))
        if avoid:
            lines.append("- Avoid drift into: " + ", ".join(str(t) for t in avoid))
        return "\n".join(lines)

    @classmethod
    def _format_sympy(cls, sympy_data: Optional[Dict[str, Any]]) -> str:
        if not sympy_data:
            return ""
        equations = sympy_data.get("symbolic_equations", [])
        steps = sympy_data.get("solution_steps", [])
        derived = sympy_data.get("derived_quantities", {})
        parts = ["SYMPY MATHEMATICAL SKELETON (verify numeric consistency):"]
        if equations:
            parts.append("Equations: " + ", ".join(str(e) for e in equations[:3]))
        if derived:
            parts.append(
                "Key quantities: "
                + ", ".join(f"{k}={v}" for k, v in list(derived.items())[:3])
            )
        if steps:
            for s in steps[:3]:
                parts.append(f"  • {s.get('step', s)}")
        return "\n".join(parts)

    @classmethod
    def build_feedback_prompt(cls, question: Dict[str, Any]) -> Tuple[str, str]:
        system = (
            "You are a mathematics question evaluator for CBSE board papers. "
            "Rate quality on a 1–5 scale per criterion."
        )
        user = f"""Evaluate this question:

Stem: {question.get('question', question.get('content', ''))}
Model answer: {question.get('correct_answer', question.get('answer', ''))}
Marks: {question.get('marks', '')}
Target difficulty: {question.get('difficulty', '')}
Chapter: {question.get('locked_chapter', question.get('chapter', ''))}

Rate 1–5 for:
- correctness: Mathematics and signs correct?
- difficulty_match: Matches target band (prove+Hence if L5)?
- novelty: Original stem, not a corpus copy?
- clarity: Self-contained, exam-style compression?
- solvability: All givens present; Hence chain valid?

Respond as JSON: {{"correctness": int, "difficulty_match": int, "novelty": int, "clarity": int, "solvability": int, "overall": float, "feedback": "..."}}"""
        return system, user
