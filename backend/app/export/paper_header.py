"""PDF / paper header helpers — time and title match marks and delivery size."""
from __future__ import annotations

import re
from typing import Any, Dict


def resolve_exam_duration(total_marks: float, question_count: int) -> str:
    """Board papers: 3h/80+ marks. Internal 5–6 question papers: 1 hour."""
    m = float(total_marks or 0)
    n = int(question_count or 0)
    if m >= 80 or n >= 10:
        return "3 Hours"
    if m <= 35 or n <= 6:
        return "1 Hour"
    return "1 Hour 30 Minutes"


def sanitize_paper_title(
    title: str,
    *,
    subject: str = "Mathematics",
    topic_focus: str = "",
) -> str:
    """Replace garbage UI titles (e.g. 'test 222', 'xcku') with a readable default."""
    t = (title or "").strip()
    if not t:
        topic = (topic_focus or "Assessment").strip()
        return f"{subject} — {topic}" if topic else f"{subject} Assessment"
    if len(t) > 48:
        return t[:48]
    low = t.lower()
    if re.search(
        r"\b(assessment|paper|quiz|examination|mathematics|maths|math)\b",
        low,
    ):
        return t
    if re.fullmatch(r"[a-z0-9][a-z0-9\s\-_.]{0,14}", low) and not re.search(
        r"\d{4}", t
    ):
        topic = (topic_focus or "Quadratic Equations").strip()
        return f"{subject} — {topic}"
    return t


def header_row_for_config(config: Dict[str, Any], total_marks: float, question_count: int) -> list:
    subject = (config.get("subject") or "").strip() or "Mathematics"
    class_level = (config.get("class_level") or "").strip() or "10"
    from datetime import datetime

    date_str = datetime.now().strftime("%d %B %Y")
    duration = resolve_exam_duration(total_marks, question_count)
    teacher = (config.get("examiner_name") or "Teacher").strip() or "Teacher"
    return [
        [f"Subject: {subject}", f"Class: {class_level}", f"Date: {date_str}"],
        [
            f"Time: {duration}",
            f"Total Marks: {int(total_marks)}",
            f"Examiner: {teacher}",
        ],
    ]
