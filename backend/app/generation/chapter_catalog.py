"""
Chapter catalog — CBSE-ingested topics + rule packs for UI selection.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.generation.chapter_rule_packs import CHAPTER_RULES, get_chapter_rule_pack
from app.generation.theorem_coverage import infer_required_theorems

# Display titles for CBSE-classified chapters without a full rule pack
_CHAPTER_DISPLAY: Dict[str, str] = {
    "linear_equations": "Linear Equations",
    "real_numbers": "Real Numbers",
    "polynomials": "Polynomials",
    "coordinate_geometry": "Coordinate Geometry",
    "statistics": "Statistics",
    "probability": "Probability",
    "arithmetic": "Arithmetic Progressions",
    "mensuration": "Mensuration",
    "surface_volume": "Surface Areas & Volumes",
}

# Sensible defaults when no rule pack exists
_DEFAULT_TYPES: tuple[str, ...] = (
    "ShortAnswer",
    "LongAnswer",
    "MCQ",
    "CaseStudy",
    "FigureBased",
)

_ALL_UI_TYPES: List[str] = [
    "MCQ",
    "ShortAnswer",
    "LongAnswer",
    "FigureBased",
    "TrueFalse",
    "FillBlank",
    "AssertionReason",
    "MatchColumn",
    "CaseStudy",
]


def _display_title(chapter_key: str) -> str:
    pack = CHAPTER_RULES.get(chapter_key)
    if pack:
        return pack.display_title
    return _CHAPTER_DISPLAY.get(
        chapter_key, chapter_key.replace("_", " ").title()
    )


def _relevant_question_types(chapter_key: str) -> List[str]:
    pack = get_chapter_rule_pack(chapter_key)
    seen: set[str] = set()
    ordered: List[str] = []
    for t in pack.preferred_question_types:
        if t not in seen and t in _ALL_UI_TYPES:
            seen.add(t)
            ordered.append(t)
    if not ordered:
        ordered = list(_DEFAULT_TYPES)
    # Geometry-heavy chapters: ensure FigureBased appears when pack allows it
    if pack.max_figure_based_count > 0 and "FigureBased" not in seen:
        if "FigureBased" in pack.preferred_question_types or chapter_key in (
            "circles",
            "triangles",
            "quadrilaterals",
        ):
            ordered.insert(0, "FigureBased")
    return ordered


def list_available_chapters() -> List[Dict[str, Any]]:
    """All selectable topics: rule packs + CBSE reference index."""
    from app.generation.cbse_reference_ingest import load_cbse_reference_manifest

    manifest = load_cbse_reference_manifest()
    cbse_counts: Dict[str, int] = manifest.get("chapters") or {}
    keys = set(CHAPTER_RULES.keys()) | set(cbse_counts.keys())
    keys.discard("generic")

    rows: List[Dict[str, Any]] = []
    for key in sorted(keys):
        pack = CHAPTER_RULES.get(key)
        rows.append(
            {
                "chapter_key": key,
                "display_title": _display_title(key),
                "cbse_stem_count": int(cbse_counts.get(key, 0)),
                "has_rule_pack": pack is not None,
                "relevant_question_types": _relevant_question_types(key),
                "max_figure_based": pack.max_figure_based_count if pack else 2,
            }
        )
    rows.sort(
        key=lambda r: (-r["cbse_stem_count"], r["display_title"].lower())
    )
    return rows


def build_chapter_topic_profile(
    chapter_key: str,
    *,
    class_level: str = "",
    topic_focus: str = "",
    subject: str = "Mathematics",
) -> Dict[str, Any]:
    """Topic profile without an uploaded PDF — CBSE curriculum mode."""
    key = (chapter_key or "generic").strip().lower()
    pack = get_chapter_rule_pack(key)
    from app.generation.cbse_reference_ingest import load_cbse_reference_manifest

    manifest = load_cbse_reference_manifest()
    cbse_count = int((manifest.get("chapters") or {}).get(key, 0))

    return {
        "document_id": "",
        "primary_topic": pack.display_title,
        "locked_chapter": key,
        "locked_chapter_source": "user_selected",
        "confidence": 1.0 if key != "generic" else 0.5,
        "subject": subject,
        "class_level": class_level,
        "subtopics": [],
        "secondary_chapters": [],
        "required_theorems": infer_required_theorems(
            key,
            blob=topic_focus or pack.display_title,
        ),
        "retrieval_confidence": 0.0,
        "generation_mode": "cbse_curriculum",
        "sample_pages": [],
        "chunk_count_used": 0,
        "total_chunks_db": 0,
        "index_status": "cbse_reference",
        "cbse_stem_count": cbse_count,
        "relevant_question_types": _relevant_question_types(key),
        "agents": ["cbse_reference", "curriculum_archetypes"],
    }
