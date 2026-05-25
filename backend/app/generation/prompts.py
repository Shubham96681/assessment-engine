"""
Prompt Builder — crafts precise, Bloom's-aligned prompts for each question type
"""
from typing import List, Optional
from app.schemas import QuestionType, BloomLevel, FigureType
from app.generation.content_profile import (
    build_chapter_alignment,
    build_content_profile,
)
from app.generation.rd_archetypes import detect_chapter_key
from app.generation.author_styles import resolve_author_style, author_style_prompt_block
from app.generation.prompt_compiler import PromptCompiler, build_semantic_plan
from app.generation.semantic_generation_plan import SemanticGenerationPlan


BLOOM_VERBS = {
    "Remember": ["Define", "List", "Recall", "Identify", "Name", "State", "Label"],
    "Understand": ["Explain", "Describe", "Summarize", "Classify", "Illustrate", "Interpret"],
    "Apply": ["Solve", "Demonstrate", "Calculate", "Use", "Apply", "Show", "Construct"],
    "Analyze": ["Compare", "Differentiate", "Examine", "Break down", "Distinguish", "Contrast"],
    "Evaluate": ["Justify", "Critique", "Assess", "Judge", "Argue", "Defend", "Evaluate"],
    "Create": ["Design", "Propose", "Formulate", "Construct", "Develop", "Plan", "Create"],
}

def _format_exclude_prior_block(stems: Optional[List[str]]) -> str:
    if not stems:
        return ""
    lines = "\n".join(f"- {s[:200]}" for s in stems[:25])
    return f"""
## NEVER REPEAT (mandatory)
These stems were already used for this user/chapter. Write **entirely new** questions:
- Different numbers, point labels, construction, and archetype
- No paraphrase of the stems below
- **Still follow** the paper dependency graph / slot roles (Q1 anchor → Q2 Hence → … → Q5 fusion)
- Change radii pairs, tangent lengths, and external point names every generation
{lines}
"""


JSON_FORMAT_NOTE = """
CRITICAL: Return ONLY a valid JSON array. No markdown, no preamble, no explanation.
Start your response with [ and end with ].
"""

# RD Sharma / RS Aggarwal — human textbook behavior (see RD_SHARMA_CLASS10_REFERENCE.md)
TEXTBOOK_EXERCISE_STYLE = """
TARGET: Real **RD Sharma / RS Aggarwal** exercises — mathematically correct, compressed, uneven, human.
NOT: AI worksheets, meta-instructions, trap explanations, or uniform symmetry.

## Stem compression (mandatory)
| Band | Words |
| L1 direct | 12–25 |
| L2–L3 | 20–40 |
| L5 HOTS | 35–60 |
| One-line conceptual | 8–18 (occasional only) |

Example: __CHAPTER_EXAMPLE__

## BANNED FOREVER (instant reject)
Use the diagram; Show your working; Justify briefly; Students often; Using theorem;
Hence prove; Analyze; Examine; configuration; situation; mechanical-geometric;
With reference to; Several lines are drawn; Study the diagram.

## Hidden theorem & invisible traps
- Never name the theorem in the stem.
- Never explain the trap ("students often subtract…").
- Wrong shortcuts appear only as MCQ distractors or in the model answer.

## Human rough edges
- Uneven difficulty: easy → medium → **spike** → easier conceptual → HOTS.
- Mix: one-line question, direct find, proof-only, (i)(ii) sometimes, unequal marks.
- Do NOT over-specify geometry ("segment lies along tangent…").

## Chapter pattern frequencies
__ARCHETYPE_TABLE__

## Elite human habits (blueprint)
- **Exercise memory:** early item teaches a pattern; later item reuses it disguised.
- **Sparse hard:** one item with minimal stem, disproportionately deep answer.
- **Visual style:** repeat author figure habits (dashed radii, tangent placement).
- **Imperfect compression:** ~1 in 4 stems may keep slight redundancy — not AI-perfect.

## Semantic completeness (mandatory)
- Every stem **self-contained**: all givens in text; solvable without viewing the figure.
- **Find angle X:** must name full angle (e.g. PTQ) AND give a numeric angle or length (e.g. angle AOB = 110°).
- **OR:** both alternatives same archetype; each half has its own givens.
- BAN awkward idiom: "passes through the perpendicular" — use "OT is perpendicular to tangent TR at T".

## Minimum context (even when compressed)
| Type | Required in stem |
| Prove PA = PB | external point + tangents named (e.g. From P, tangents PA and PB to a circle…) |
| Find angle | full angle symbol + numeric given; centre angle uses radii arms (AOB not POQ when tangents are TA, TB) |
| Tangent length | tangent point, centre, segment lengths |
| Never | bare "Prove that PA = PB." with no construction |

## HARD UI difficulty (when tier is hard)
{hard_block}

{numeric_block}

__IDIOMATIC_BLOCK__

## Model answers
- Given → Step 1 → … → Hence; theorems named **only here**.
- Real difficulty = theorem chain length in the answer, not stem length.

Marks: MCQ/AR=1; VSA=2–3; SA=3–4; LA=5–6; FigureBased=4–6; CaseStudy=4–5
"""

CBSE_PYQ_STYLE = TEXTBOOK_EXERCISE_STYLE


def format_textbook_style(chapter: str = "generic", difficulty: str = "medium") -> str:
    from app.generation.content_profile import ContentProfile

    if (difficulty or "").lower() in ("hard", "difficult"):
        hard_block = build_chapter_hard_prompt_stack(chapter, difficulty)
    else:
        hard_block = "(Not applicable — use standard mix.)"
    profile = ContentProfile(
        chapter_key=chapter,
        subject="Mathematics",
        class_label="10",
        filename="",
        chapter_title=chapter.replace("_", " ").title(),
    )
    example = build_figure_stem_example(profile)
    return (
        TEXTBOOK_EXERCISE_STYLE.replace(
            "__ARCHETYPE_TABLE__", archetype_prompt_block(chapter)
        )
        .replace("__CHAPTER_EXAMPLE__", example)
        .replace("__IDIOMATIC_BLOCK__", idiomatic_prompt_block(chapter))
        .replace("{hard_block}", hard_block)
        .replace("{numeric_block}", "")
    )


class PromptBuilder:
    def build(
        self,
        question_type: QuestionType,
        difficulty: str,
        bloom_level,
        context: str,
        count: int,
        subject: Optional[str] = None,
        class_level: Optional[str] = None,
        topic_focus: Optional[str] = None,
        exclude_topics: Optional[str] = None,
        language: str = "English",
        generation_num: int = 1,
        figure_types: Optional[List] = None,
        instructions: Optional[str] = None,
        document_filename: Optional[str] = None,
        exclude_prior_stems: Optional[List[str]] = None,
        locked_chapter: str = "",
        required_theorems: Optional[List] = None,
        retrieval_confidence: float = 0.0,
        use_curriculum_archetypes: bool = False,
        student_skill_block: str = "",
        memory_block: str = "",
        rejection_block: str = "",
        semantic_plan: Optional[SemanticGenerationPlan] = None,
        difficulty_distribution=None,
    ) -> str:
        bloom_str = bloom_level.value if hasattr(bloom_level, "value") else str(bloom_level)
        type_str = question_type.value if hasattr(question_type, "value") else str(question_type)
        verbs = BLOOM_VERBS.get(bloom_str, ["Explain"])
        profile = build_content_profile(
            topic_focus=topic_focus or "",
            filename=document_filename or "",
            context=context[:1200],
            subject=subject or "",
            class_level=class_level or "",
            instructions=instructions or "",
            difficulty=difficulty,
        )
        chapter = locked_chapter or profile.chapter_key
        profile.chapter_key = chapter
        author = resolve_author_style(instructions=instructions)

        if semantic_plan is None:
            semantic_plan = build_semantic_plan(
                locked_chapter=chapter,
                question_count=count,
                question_types=[question_type],
                difficulty=difficulty,
                bloom_level=bloom_level,
                profile=profile,
                required_theorems=required_theorems,
                retrieval_confidence=retrieval_confidence,
                use_curriculum_archetypes=use_curriculum_archetypes,
                context=context,
                exclude_prior_stems=exclude_prior_stems,
                student_skill_block=student_skill_block,
                memory_block=memory_block,
                rejection_block=rejection_block,
                instructions=instructions or "",
                generation_num=generation_num,
                author=author,
                difficulty_distribution=difficulty_distribution,
            )

        builder = {
            "MCQ": self._mcq_prompt,
            "ShortAnswer": self._short_answer_prompt,
            "LongAnswer": self._long_answer_prompt,
            "FigureBased": self._figure_based_prompt,
            "TrueFalse": self._true_false_prompt,
            "FillBlank": self._fill_blank_prompt,
            "AssertionReason": self._assertion_reason_prompt,
            "MatchColumn": self._match_column_prompt,
            "CaseStudy": self._case_study_prompt,
        }.get(type_str, self._short_answer_prompt)

        lang_block = ""
        if language and language.strip().lower() not in ("english", "en"):
            lang_block = (
                f"\nOUTPUT LANGUAGE: {language}\n"
                f"- Write every question stem, options, and model answer in {language}.\n"
                f"- Keep mathematical symbols and numbers universal; use {language} for wording only.\n"
            )

        compiler = PromptCompiler.from_plan(semantic_plan)
        core = compiler.compile_core()
        effective = semantic_plan.effective_question_types()
        if len(set(effective)) > 1 or (
            chapter == "quadratic" and type_str == "FigureBased"
        ):
            type_tail = self._mixed_chapter_paper_tail(
                semantic_plan, difficulty, bloom_str, verbs, figure_types
            )
        elif type_str == "FigureBased":
            type_tail = self._figure_based_prompt(
                count, difficulty, bloom_str, verbs, figure_types, chapter=chapter
            )
        else:
            type_tail = builder(count, difficulty, bloom_str, verbs, figure_types)
        extra = ""
        if lang_block:
            extra += lang_block
        if instructions:
            extra += f"\nSpecial Instructions: {instructions}\n"
        if topic_focus:
            extra += f"\nTopic Focus: {topic_focus}\n"
        if exclude_topics:
            extra += f"\nExclude: {exclude_topics}\n"
        return core + "\n\nTYPE-SPECIFIC OUTPUT:\n" + type_tail + extra

    def _mcq_prompt(self, count, difficulty, bloom, verbs, _):
        step_rule = {
            "easy": "2–3 steps to eliminate options.",
            "medium": "3–4 steps; hidden theorem may be required.",
            "hard": "4+ steps or trap (common wrong formula as distractor).",
        }.get(difficulty, "Multi-step.")
        return f"""
Generate exactly {count} RD Sharma / RS Aggarwal MCQs (1 mark, board Section A style).
Rules:
- **One short stem** (1–2 sentences max) with numerical givens, then four options
- Each MCQ: exactly 4 options (A), (B), (C), (D)
- {step_rule}
- Command style: "Find …", "If … then … equals", "The value of … is" — NOT "Which statement…"
- Distractors = wrong intermediate values (sign error, wrong theorem, arithmetic slip)
- BAN: definition-only, "All/None of the above", essay stems
- marks: 1; Bloom: {bloom}; difficulty: {difficulty}

Return JSON array:
[
  {{
    "question": "Question text here?",
    "options": [
      {{"label": "A", "text": "Option A text", "is_correct": false}},
      {{"label": "B", "text": "Option B text", "is_correct": true}},
      {{"label": "C", "text": "Option C text", "is_correct": false}},
      {{"label": "D", "text": "Option D text", "is_correct": false}}
    ],
    "answer": "B",
    "explanation": "Why B is correct and others are wrong."
  }}
]
{JSON_FORMAT_NOTE}"""

    def _short_answer_prompt(self, count, difficulty, bloom, verbs, _):
        marks = {"easy": 2, "medium": 3, "hard": 4}.get(difficulty, 3)
        steps = {"easy": "3–4", "medium": "4–5", "hard": "5–7"}.get(difficulty, "4+")
        return f"""
Generate exactly {count} Short Answer questions — RD Sharma VSA / SA style ({marks} marks each).
Rules:
- **Compact stem:** 1–2 sentences (≤80 words); givens + Find/Prove/Show that
- Model answer: **{steps} steps** with theorem names
- ~30% include **OR** (same marks); hard may use (i)(ii) one line each
- BAN: "Examine/Analyze…", paragraph stems, answers without working
- marks: {marks}; difficulty: {difficulty}

Return JSON array:
[
  {{
    "question": "Question text (include OR part if two alternatives)?",
    "marks": {marks},
    "answer": "Model answer with steps",
    "explanation": "Marking scheme value points"
  }}
]
{JSON_FORMAT_NOTE}"""

    def _long_answer_prompt(self, count, difficulty, bloom, verbs, _):
        return f"""
Generate exactly {count} RD Sharma Long Answer questions (5–6 marks each).
Rules:
- Main stem ≤ 60 words; sub-parts (i), (ii), (iii) as **short lines** (Hence / OR allowed)
- Proof or derivation + numeric follow-up; multi-concept on hard
- At least one **OR** if count >= 2
- Model answer: numbered steps + Hence; marking scheme in explanation
- BAN: long essay introductions before (i)(ii)
- marks: 5 or 6; Bloom: {bloom}; difficulty: {difficulty}

Return JSON array:
[
  {{
    "question": "Full LA stem with (i), (ii) sub-parts if needed",
    "marks": 5,
    "answer": "Detailed model solution with steps",
    "explanation": "Marking scheme (½ + ½ + 1 + … value points)"
  }}
]
{JSON_FORMAT_NOTE}"""

    def _mixed_chapter_paper_tail(
        self,
        plan: SemanticGenerationPlan,
        difficulty: str,
        bloom: str,
        verbs,
        figure_types,
    ) -> str:
        """Per-slot types from chapter pack — not 'Generate exactly N FigureBased'."""
        pack = plan.rule_pack
        lines = [
            f"Generate exactly {plan.question_count} questions — {pack.display_title} native mix:",
            f"- Max {pack.max_figure_based_count} FigureBased (diagram/table only when necessary).",
            "- Slot types (mandatory):",
        ]
        for s in plan.slots:
            qtype = s.question_type or plan.effective_question_types()[
                (s.slot - 1) % len(plan.effective_question_types())
            ]
            lines.append(f'  id "{s.slot}": {qtype}')
        lines.append(
            "- ShortAnswer/LongAnswer: compressed stems, 3–7 step model answers.\n"
            "- CaseStudy: 100–140 word scenario with numeric sub-parts.\n"
            "- MCQ: one stem + four options; distractors = wrong intermediate values.\n"
            "- FigureBased ONLY for area/speed/table models — never bare factorisation with a circle diagram."
        )
        return "\n".join(lines) + f"\n{JSON_FORMAT_NOTE}"

    def _figure_based_prompt(self, count, difficulty, bloom, verbs, figure_types, chapter: str = "generic"):
        from app.generation.chapter_rule_packs import get_chapter_rule_pack

        pack = get_chapter_rule_pack(chapter)
        fig_list = ", ".join(
            [f.value if hasattr(f, "value") else str(f) for f in (figure_types or list(pack.figure_types))]
        )
        length_rules = f"""
FIGURE-BASED — diagram drawn separately; stem = compressed maths only:
- Words: 20–55 typical; HOTS up to 60. BAN Show your working / Use the diagram / Students often.
- Example ({pack.display_title}): "{pack.stem_example}"
- Allowed figure types: {", ".join(pack.figure_types)} — no circle diagrams unless chapter is Circles.
- Progress figure complexity Q1 simple → Q5 dense (see blueprint).
- Labels A–Z; figure_spec.title = "Diagram"; no over-specification of segments.
"""
        hard_rules = ""
        if difficulty == "hard":
            hard_rules = """
HARD: uneven marks (4–6); (i)(ii) on some items only; OR on one; invisible trap in one numeric item.
FULL HARD (100% slider): NO direct Pythagoras Q1; NO standard NCERT one-shot proofs; every item needs
3+ hidden reasoning steps, multi-theorem fusion, proof+Hence or tangent–secant power on at least one slot.
"""
        elif difficulty == "medium":
            hard_rules = """
MEDIUM: 20–40 words; one theorem + find.
"""
        else:
            hard_rules = """
EASY: 15–30 words; direct find.
"""
        if chapter == "quadratic":
            count_note = (
                f"Generate up to {min(count, pack.max_figure_based_count)} Figure-Based items "
                f"and remaining slots as ShortAnswer/LongAnswer/CaseStudy per blueprint."
            )
        else:
            count_note = f"Generate exactly {count} Figure-Based Questions (RD Sharma exercise tone)."
        return f"""
{count_note}
Available figure types: {fig_list}
Rules:
- ORIGINAL questions from SOURCE; figure_spec required for labeled_diagram
- BAN: Examine/Analyze/Study the diagram/mechanical-geometric/long essay stems
{length_rules}
{hard_rules}
Return JSON array:
[
  {{
    "id": "1",
    "type": "FigureBased",
    "question": "{pack.stem_example}",
    "marks": {5 if difficulty == "hard" else 4},
    "figure_type": "{pack.figure_types[0]}",
    "figure_spec": {{
      "type": "{pack.figure_types[0]}",
      "title": "Diagram",
      "elements": [
        {{"shape": "point", "label": "A", "position": "inside"}},
        {{"shape": "point", "label": "B", "position": "inside"}},
        {{"shape": "segment", "from": "A", "to": "B"}}
      ],
      "labels": {{"A": "A", "B": "B"}}
    }},
    "correct_answer": "Full model answer with steps",
    "explanation": "Marking scheme / key steps"
  }}
]
{JSON_FORMAT_NOTE}"""

    def _true_false_prompt(self, count, difficulty, bloom, verbs, _):
        return f"""
Generate exactly {count} True/False Questions.
Rules:
- Half should be True, half should be False
- False statements must be subtly wrong (not obviously wrong)
- Include justification

Return JSON array:
[
  {{
    "question": "Statement to evaluate as True or False.",
    "answer": "True",
    "explanation": "Why this statement is True/False with reference to content."
  }}
]
{JSON_FORMAT_NOTE}"""

    def _fill_blank_prompt(self, count, difficulty, bloom, verbs, _):
        return f"""
Generate exactly {count} Fill-in-the-Blank Questions.
Rules:
- Use _______ to indicate blank(s)
- Each question should have 1-2 blanks max
- Blanks should be key terms/concepts, not trivial words

Return JSON array:
[
  {{
    "question": "The process of _______ converts glucose into energy in the presence of _______.",
    "answer": "cellular respiration | oxygen",
    "explanation": "Explanation of why these are the correct answers."
  }}
]
{JSON_FORMAT_NOTE}"""

    def _assertion_reason_prompt(self, count, difficulty, bloom, verbs, _):
        return f"""
Generate exactly {count} Assertion-Reason Questions.
Format: 
  Assertion (A): [Statement]
  Reason (R): [Statement]
Options always:
  A) Both A and R are true, and R is the correct explanation of A
  B) Both A and R are true, but R is NOT the correct explanation of A
  C) A is true but R is false
  D) A is false but R is true

Return JSON array:
[
  {{
    "question": "Assertion (A): [assertion text]\\nReason (R): [reason text]\\n\\n(A) Both A and R are true, and R is the correct explanation of A\\n(B) Both A and R are true, but R is NOT the correct explanation of A\\n(C) A is true but R is false\\n(D) A is false but R is true",
    "options": [
      {{"label": "A", "text": "Both A and R are true, and R is the correct explanation of A", "is_correct": true}},
      {{"label": "B", "text": "Both A and R are true, but R is NOT the correct explanation of A", "is_correct": false}},
      {{"label": "C", "text": "A is true but R is false", "is_correct": false}},
      {{"label": "D", "text": "A is false but R is true", "is_correct": false}}
    ],
    "answer": "A",
    "explanation": "Full explanation of the assertion-reason relationship."
  }}
]
{JSON_FORMAT_NOTE}"""

    def _match_column_prompt(self, count, difficulty, bloom, verbs, _):
        return f"""
Generate exactly {count} Match the Column Questions.
Rules:
- Column A should have 5 items, Column B should have 5 matching items (possibly shuffled)
- Include one extra in Column B as a distractor if difficulty is hard

Return JSON array:
[
  {{
    "question": "Match Column A with Column B:\\n\\nColumn A:\\n1. [Item 1]\\n2. [Item 2]\\n3. [Item 3]\\n4. [Item 4]\\n5. [Item 5]\\n\\nColumn B:\\na. [Match a]\\nb. [Match b]\\nc. [Match c]\\nd. [Match d]\\ne. [Match e]",
    "answer": "1-c, 2-a, 3-e, 4-b, 5-d",
    "explanation": "Explanation of each correct match."
  }}
]
{JSON_FORMAT_NOTE}"""

    def _case_study_prompt(self, count, difficulty, bloom, verbs, _):
        return f"""
Generate exactly {count} Case Study questions — board Section E format, RS Aggarwal application level (4–5 marks).
Rules:
- 100–140 word scenario with concrete numbers (tables, distances, angles) from SOURCE themes
- Sub-parts (i), (ii), (iii): at least one needs 3+ steps; one may be Prove/Show that
- One sub-part may offer OR alternative
- Do not use generic "a shopkeeper" without data — embed values students must use
- marks: 4 or 5; difficulty: {difficulty}

Return JSON array:
[
  {{
    "question": "CASE STUDY:\\n[scenario]\\n\\nBased on the above, answer:\\n(i) ...\\nOR\\n(ii) ...\\n(iii) ...",
    "marks": 4,
    "answer": "(i) ...\\n(ii) ...\\n(iii) ...",
    "explanation": "Marking rubric per sub-part"
  }}
]
{JSON_FORMAT_NOTE}"""
