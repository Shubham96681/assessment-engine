"""
Exam pattern metadata — section counts, marks, figure ratios (config reference).

Used for future JEE / full-board paper generation; not yet wired to the generator.
"""
from __future__ import annotations

from typing import Any, Dict, List

EXAM_PATTERNS: Dict[str, Dict[str, Any]] = {
    "CBSE_Class10_Math": {
        "total_marks": 80,
        "duration_minutes": 180,
        "sections": [
            {"name": "A", "type": "mcq", "questions": 20, "marks_each": 1, "figure_ratio": 0.2},
            {"name": "B", "type": "very_short", "questions": 5, "marks_each": 2, "figure_ratio": 0.4},
            {"name": "C", "type": "short", "questions": 6, "marks_each": 3, "figure_ratio": 0.5},
            {"name": "D", "type": "long", "questions": 4, "marks_each": 5, "figure_ratio": 0.7},
            {"name": "E", "type": "case_study", "questions": 3, "marks_each": 4, "figure_ratio": 0.8},
        ],
        "topics": [
            "Real Numbers",
            "Polynomials",
            "Pair of Linear Equations",
            "Quadratic Equations",
            "Arithmetic Progressions",
            "Triangles",
            "Coordinate Geometry",
            "Introduction to Trigonometry",
            "Applications of Trigonometry",
            "Circles",
            "Areas Related to Circles",
            "Surface Areas and Volumes",
            "Statistics",
            "Probability",
        ],
    },
    "JEE_Mains_Math": {
        "total_marks": 100,
        "duration_minutes": 180,
        "sections": [
            {"name": "A", "type": "mcq", "questions": 20, "marks_each": 4, "negative": 1},
            {"name": "B", "type": "integer", "questions": 5, "marks_each": 4, "negative": 0},
            {"name": "C", "type": "matching", "questions": 5, "marks_each": 4, "negative": 1},
        ],
    },
}


def list_exam_patterns() -> List[Dict[str, Any]]:
    return [{"id": k, **v} for k, v in EXAM_PATTERNS.items()]
