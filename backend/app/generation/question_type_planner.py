"""
Resolve per-slot question types — geometry chapters get enough FigureBased items.
"""
from __future__ import annotations

from typing import List

from app.generation.chapter_rule_packs import ChapterRulePack

_GEOMETRY_CHAPTERS = frozenset(
    {"circles", "triangles", "quadrilaterals", "trigonometry"}
)


def _figure_target(question_count: int, max_figure: int, chapter: str) -> int:
    if max_figure <= 0:
        return 0
    if chapter == "circles":
        return min(max_figure, question_count)
    ratio = (question_count * 3 + 4) // 5
    return min(max_figure, max(2, ratio))


def resolve_effective_question_types(
    *,
    chapter: str,
    pack: ChapterRulePack,
    types: List[str],
    question_count: int,
    ui_difficulty: str = "medium",
) -> List[str]:
    """
    Per-slot types for the paper. Geometry chapters with diagram support
    assign FigureBased to most slots even when the UI only selected MCQ/ShortAnswer.
    """
    preferred = list(pack.preferred_question_types)
    if not preferred:
        preferred = ["ShortAnswer"]

    n = max(1, int(question_count))
    ch = (chapter or "generic").strip().lower()
    ui = (ui_difficulty or "medium").lower()
    max_fb = int(pack.max_figure_based_count or 0)

    if types and ch == "quadratic" and all(t == "FigureBased" for t in types):
        return preferred[:n] if len(preferred) >= n else (preferred * 2)[:n]

    if ch == "circles" and max_fb > 0:
        return (preferred * ((n // len(preferred)) + 1))[:n]

    if ch in _GEOMETRY_CHAPTERS and max_fb > 0 and ui in ("hard", "difficult", "medium"):
        n_fig = _figure_target(n, max_fb, ch)
        if n_fig > 0:
            non_fig = [t for t in (types or preferred) if t != "FigureBased"]
            if not non_fig:
                non_fig = [t for t in preferred if t != "FigureBased"] or ["ShortAnswer"]
            out: List[str] = ["FigureBased"] * n_fig
            for i in range(n - n_fig):
                out.append(non_fig[i % len(non_fig)])
            return out[:n]

    if not types:
        return (preferred * ((n // len(preferred)) + 1))[:n]

    if len(types) == 1:
        t0 = types[0]
        if t0 == "FigureBased" and max_fb > 0:
            return ["FigureBased"] * min(n, max_fb) + [
                preferred[i % len(preferred)]
                for i in range(max(0, n - max_fb))
            ][:n]
        return [
            t0
            if i < max_fb or t0 != "FigureBased"
            else preferred[i % len(preferred)]
            for i in range(n)
        ]

    return [types[i % len(types)] for i in range(n)]
