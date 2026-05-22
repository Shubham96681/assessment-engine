"""
Dynamic content profile — retrieval queries and generation tone follow the
selected PDF, class/exam level, and RAG context (not hardcoded Circles / Class 10).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.rd_archetypes import detect_chapter_key


@dataclass
class ContentProfile:
    """Resolved teaching context for one generation run."""

    exam_track: str = "board"  # board | jee_mains | jee_advanced | foundation | olympiad | generic
    chapter_key: str = "generic"
    chapter_title: str = ""
    subject: str = "Mathematics"
    class_label: str = ""
    topic_focus: str = ""
    filename: str = ""
    context_headline: str = ""
    style_label: str = "textbook exercise"
    difficulty_tone: str = "medium"

    def display_class(self) -> str:
        if self.class_label:
            return self.class_label
        if self.exam_track == "jee_advanced":
            return "JEE Advanced"
        if self.exam_track == "jee_mains":
            return "JEE Main"
        return "10"


def _slug_words(text: str) -> str:
    t = re.sub(r"[_\.\-]+", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_filename_hints(filename: str) -> Dict[str, str]:
    """Extract class, subject, chapter from common PDF naming patterns."""
    out: Dict[str, str] = {}
    if not filename:
        return out
    stem = filename.rsplit(".", 1)[0]
    low = stem.lower()

    m = re.search(r"\bclass[\s_\-]*(\d{1,2})\b", low, re.I)
    if m:
        out["class_num"] = m.group(1)

    m = re.search(r"\b(?:chapter|chpt|ch)[\s_\-]*(\d{1,2})\b", low, re.I)
    if m:
        out["chapter_num"] = m.group(1)

    for subj in ("maths", "mathematics", "physics", "chemistry", "biology", "science"):
        if subj in low:
            out["subject_hint"] = "Mathematics" if subj in ("maths", "mathematics") else subj.title()
            break

    if "jee" in low and "advanced" in low:
        out["exam"] = "jee_advanced"
    elif "jee" in low or "jee_main" in low or "mains" in low:
        out["exam"] = "jee_mains"
    elif "neet" in low:
        out["exam"] = "neet"
    elif "olympiad" in low or "imo" in low:
        out["exam"] = "olympiad"

    # Title segment after chapter number: Chapter_4_Quadratic_Equations
    parts = re.split(r"chapter[\s_\-]*\d+[\s_\-]*", low, maxsplit=1, flags=re.I)
    if len(parts) > 1 and parts[1].strip():
        title = _slug_words(parts[1])
        if len(title) > 3:
            out["chapter_title"] = title.title()
    else:
        # Strip class/subject tokens for a short title
        cleaned = re.sub(
            r"\b(class|maths|mathematics|physics|chemistry|ncert|rd|sharma|rs|aggarwal)\b",
            " ",
            _slug_words(stem),
            flags=re.I,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > 8:
            out["chapter_title"] = cleaned.title()[:80]

    return out


def extract_context_headline(context: str, max_len: int = 120) -> str:
    """First substantive heading line from retrieved chunks."""
    if not context:
        return ""
    for line in context.splitlines():
        line = line.strip()
        if not line or line == "." or line == "---":
            continue
        if re.match(r"^[\d\.\s]+$", line):
            continue
        if len(line) < 8:
            continue
        if "reprint" in line.lower():
            continue
        if re.search(r"^(exercise|example|activity)\s", line, re.I):
            return line[:max_len]
        if line.isupper() or re.match(r"^[A-Z][A-Za-z\s]{6,}", line):
            return line[:max_len]
    return ""


def infer_exam_track(
    *,
    class_level: str = "",
    instructions: str = "",
    filename: str = "",
    topic_focus: str = "",
) -> str:
    blob = f"{class_level} {instructions} {filename} {topic_focus}".lower()
    hints = parse_filename_hints(filename)

    if hints.get("exam"):
        return hints["exam"]
    if any(
        k in blob
        for k in (
            "jee advanced",
            "jee-advanced",
            "jeeadv",
            "iit-jee advanced",
            "paper 2",
        )
    ):
        return "jee_advanced"
    if any(
        k in blob
        for k in (
            "jee main",
            "jee mains",
            "jee-main",
            "jeemain",
            "iit-jee",
            "jee",
        )
    ):
        return "jee_mains"
    if "neet" in blob:
        return "neet"
    if any(k in blob for k in ("olympiad", "prmo", "rmo", "hots only")):
        return "olympiad"
    if any(k in blob for k in ("class 6", "class 7", "class 8", "class 9", "foundation", "ntse")):
        return "foundation"
    if re.search(r"\bclass\s*(?:11|12|xi|xii)\b", blob):
        return "board"
    if re.search(r"\bclass\s*(?:9|10)\b", blob):
        return "board"
    return "board"


def _style_for_track(exam_track: str, subject: str) -> str:
    subj = (subject or "Mathematics").lower()
    if exam_track == "jee_advanced":
        return "JEE Advanced multi-concept proof and calculation"
    if exam_track == "jee_mains":
        return "JEE Main NCERT-based numerical and assertion-style"
    if exam_track == "neet":
        return f"NEET-level {subject} application and diagram-based drill"
    if exam_track == "olympiad":
        return "Olympiad-style non-routine problems"
    if exam_track == "foundation":
        return f"Class 6–9 foundation {subject} exercises"
    if "physics" in subj:
        return "Physics numerical and concept application"
    if "chemistry" in subj:
        return "Chemistry reaction, mole concept, and reasoning items"
    return "Board textbook RD Sharma / RS Aggarwal exercise depth"


def build_content_profile(
    *,
    topic_focus: str = "",
    filename: str = "",
    context: str = "",
    subject: str = "",
    class_level: str = "",
    instructions: str = "",
    difficulty: str = "medium",
) -> ContentProfile:
    hints = parse_filename_hints(filename)
    headline = extract_context_headline(context)
    chapter_key, ch_source, ch_conf = resolve_locked_chapter(
        filename=filename,
        topic_focus=topic_focus,
        context=context,
    )
    if chapter_key == "generic":
        chapter_key = detect_chapter_key(topic_focus, filename, context)
    exam_track = infer_exam_track(
        class_level=class_level,
        instructions=instructions,
        filename=filename,
        topic_focus=topic_focus,
    )

    chapter_title = hints.get("chapter_title") or headline or topic_focus or ""
    if not chapter_title and chapter_key != "generic":
        chapter_title = chapter_key.replace("_", " ").title()

    class_label = (class_level or "").strip()
    if not class_label and hints.get("class_num"):
        class_label = f"Class {hints['class_num']}"
    if not class_label and exam_track == "jee_mains":
        class_label = "JEE Main"
    if not class_label and exam_track == "jee_advanced":
        class_label = "JEE Advanced"

    subj = (subject or hints.get("subject_hint") or "Mathematics").strip()

    return ContentProfile(
        exam_track=exam_track,
        chapter_key=chapter_key,
        chapter_title=chapter_title,
        subject=subj,
        class_label=class_label,
        topic_focus=(topic_focus or "").strip(),
        filename=filename or "",
        context_headline=headline,
        style_label=_style_for_track(exam_track, subj),
        difficulty_tone=(difficulty or "medium").lower(),
    )


def build_semantic_retrieval_query(
    *,
    profile: ContentProfile,
    config_topic_focus: str = "",
) -> str:
    """
    Qdrant query — chapter concepts and theorem vocabulary only.

    Pedagogy (hard, Analyze, FigureBased, exercise depth) belongs in the compiler prompt,
    not in the retriever.
    """
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    parts: List[str] = []
    chapter = profile.chapter_key or "generic"
    pack = get_chapter_rule_pack(chapter)

    if config_topic_focus.strip():
        parts.append(config_topic_focus.strip())
    elif profile.topic_focus:
        parts.append(profile.topic_focus)
    if profile.chapter_title:
        parts.append(profile.chapter_title)
    if profile.filename:
        parts.append(_slug_words(profile.filename.rsplit(".", 1)[0]))

    for term in pack.retrieval_semantic_terms:
        parts.append(term)
    for tid in pack.theorem_pattern_ids[:6]:
        parts.append(tid.replace("_", " "))

    if profile.context_headline:
        parts.append(profile.context_headline)

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: List[str] = []
    for p in parts:
        key = p.lower().strip()
        if key and key not in seen and len(key) > 2:
            seen.add(key)
            unique.append(p.strip())
    return " ".join(unique)


def build_rag_retrieval_query(
    *,
    task: Dict[str, Any],
    profile: ContentProfile,
    config_topic_focus: str = "",
    config_instructions: str = "",
) -> str:
    """Semantic search query for Qdrant — topic/theorems only (see build_semantic_retrieval_query)."""
    _ = task, config_instructions  # pedagogy not used for embedding retrieval
    return build_semantic_retrieval_query(
        profile=profile,
        config_topic_focus=config_topic_focus,
    )


def build_context_fallback(profile: ContentProfile) -> str:
    """When RAG returns no chunks — still anchor to selected chapter, not Circles."""
    title = profile.chapter_title or profile.topic_focus or _slug_words(
        profile.filename.rsplit(".", 1)[0]
    )
    return (
        f"Chapter context placeholder for: {title or 'selected document'}. "
        f"Subject: {profile.subject}. Level: {profile.display_class()} ({profile.exam_track}). "
        f"Generate questions only from this chapter using standard {profile.style_label}."
    )


def build_curriculum_context(
    profile: ContentProfile,
    *,
    required_theorems: Optional[List[Dict[str, str]]] = None,
    retrieval_confidence: float = 0.0,
) -> str:
    """
    Sparse PDF retrieval — anchor generation to curriculum archetypes + theorem plan.
    """
    from app.generation.theorem_coverage import build_theorem_coverage_prompt

    title = profile.chapter_title or profile.chapter_key.replace("_", " ").title()
    block = build_theorem_coverage_prompt(
        required_theorems or [],
        question_count=8,
    )
    theorem_lines = ""
    if required_theorems:
        theorem_lines = "\n".join(
            f"- {t.get('id')}: {t.get('label', '')}" for t in required_theorems[:8]
        )
    return (
        f"CURRICULUM MODE (retrieval confidence {retrieval_confidence:.2f} — sparse PDF chunks).\n"
        f"Chapter: {title} (key: {profile.chapter_key}).\n"
        f"Subject: {profile.subject} | Level: {profile.display_class()}.\n"
        f"Use standard NCERT/RD Sharma exercise patterns for this chapter only — "
        f"do NOT invent facts absent from typical syllabus coverage.\n"
        f"{block}"
        f"Required theorem coverage:\n{theorem_lines or '- standard syllabus mix'}\n"
        f"Generate original stems from these structures; vary numbers and labels.\n"
    )


def build_chapter_alignment(profile: ContentProfile) -> str:
    """Mandatory alignment block for rag_query / Cursor agent."""
    name = profile.filename or "uploaded PDF"
    title = profile.chapter_title or profile.chapter_key.replace("_", " ").title()
    lines = [
        "\nCHAPTER ALIGNMENT (mandatory):",
        f"- SELECTED DOCUMENT: {name}",
        f"- Detected chapter/topic: **{title}** (key: {profile.chapter_key}).",
        f"- Subject: {profile.subject} | Level: {profile.display_class()} | Track: {profile.exam_track}.",
        "- Use ONLY facts and structures from CONTEXT above — do not switch to another chapter.",
    ]

    if profile.chapter_key == "quadratic":
        lines.append(
            "- Generate quadratic equations / discriminant / roots / word problems only."
        )
        lines.append("- No unrelated geometry chapters in this paper.")
    elif profile.chapter_key == "quadrilaterals":
        lines.append("- Generate parallelogram / rhombus / trapezium / diagonal proofs only.")
        lines.append("- Do NOT use circle tangents or secant power.")
    elif profile.chapter_key == "circles":
        lines.append("- Circle, tangent, secant, chord geometry only.")
    elif profile.chapter_key != "generic":
        lines.append(f"- Stay on **{title}** concepts from this PDF.")

    if profile.exam_track == "jee_advanced":
        lines.append(
            "- JEE Advanced: multi-step fusion, rigorous reasoning, no primary-school recall."
        )
    elif profile.exam_track == "jee_mains":
        lines.append(
            "- JEE Main: NCERT-plus numerical speed, single-paper mixed concepts, trap options ok in MCQ."
        )
    elif profile.exam_track == "foundation":
        lines.append("- Foundation level: clear givens, 2–4 steps, no JEE-only tricks.")

    if profile.chapter_key == "circles":
        lines.append("- HARD MODE geometry rules in this prompt apply to Circles only.")
    else:
        lines.append("- Apply only the HARD MODE block for the locked chapter above.")
    return "\n".join(lines) + "\n"


def build_figure_stem_example(profile: ContentProfile) -> str:
    if profile.chapter_key == "quadratic":
        return (
            "'A rectangular plot has length 2x+1 m and breadth x m. Area is 300 m². Form the equation and find x.'"
        )
    if profile.chapter_key == "circles":
        return "'PQ is a tangent at P. O is centre, OP = 5 cm, OQ = 12 cm. Find PQ.'"
    if profile.chapter_key == "quadrilaterals":
        return "'Parallelogram ABCD has diagonals intersecting at O. If AO = 6 cm, find AC.'"
    return "'Use givens from the chapter; find the required quantity in 3–5 steps.'"


def build_difficulty_rubric(profile: ContentProfile, difficulty: str) -> str:
    diff = (difficulty or "medium").lower()
    if profile.exam_track == "jee_advanced":
        return {
            "easy": "Minimum 3–4 steps; one core idea from CONTEXT.",
            "medium": "Minimum 5–6 steps; combine two ideas; may use substitution or case split.",
            "hard": "Minimum 7+ steps; JEE Advanced fusion, rigorous Hence chain, OR branch encouraged.",
        }.get(diff, "Multi-step JEE Advanced.")
    if profile.exam_track == "jee_mains":
        return {
            "easy": "Minimum 2–3 steps; direct NCERT application.",
            "medium": "Minimum 4–5 steps; one twist or hidden step.",
            "hard": "Minimum 6+ steps; time-efficient multi-concept, numerical trap ok.",
        }.get(diff, "Multi-step JEE Main.")
    return {
        "easy": "Minimum 2–3 reasoning steps per item (Level-I exercise — NOT recall).",
        "medium": "Minimum 4–5 steps; combine two ideas from CONTEXT.",
        "hard": "Minimum 6+ steps; HOTS; proofs with Hence; OR alternatives encouraged.",
    }.get(diff, "Multi-step only.")
