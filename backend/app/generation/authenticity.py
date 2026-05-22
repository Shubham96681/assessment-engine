"""
Textbook authenticity detector — rejects AI worksheet signals.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple

from app.generation.textbook_constants import (
    BANNED_META_PHRASES,
    BANNED_OVER_SPEC,
    STEM_WORD_TARGETS,
    FIGURE_STEM_WORD_TARGETS,
)
from app.generation.solution_difficulty import score_solution_difficulty


class TextbookAuthenticityScorer:
    """Does this read like RD Sharma / RS Aggarwal, not an AI worksheet?"""

    REJECT_THRESHOLD = 0.45
    PASS_THRESHOLD = 0.62

    def score_question(self, q: Dict[str, Any], slot_band: str = "L3") -> Dict[str, Any]:
        content = (q.get("content") or "").strip()
        lower = content.lower()
        n_words = len(content.split())
        qtype = q.get("question_type") or ""

        score = 0.72
        flags: List[str] = []

        meta_hits = [p for p in BANNED_META_PHRASES if p in lower]
        if meta_hits:
            score -= min(0.55, len(meta_hits) * 0.12)
            flags.append(f"meta_language:{meta_hits[0]}")

        over_hits = [p for p in BANNED_OVER_SPEC if p in lower]
        if over_hits:
            score -= min(0.2, len(over_hits) * 0.06)
            flags.append("over_specified")

        if lower.startswith("in the adjoining figure") and n_words < 40:
            score -= 0.04

        targets = FIGURE_STEM_WORD_TARGETS if qtype == "FigureBased" else STEM_WORD_TARGETS
        lo, hi = targets.get(slot_band, targets.get("L3", (20, 40)))

        if n_words > hi + 15:
            score -= 0.18
            flags.append("stem_too_long")
        elif n_words < lo - 5 and qtype != "FigureBased":
            if not self._is_one_line_conceptual(content):
                score -= 0.1
                flags.append("stem_too_thin")
        elif lo <= n_words <= hi:
            score += 0.12
        elif n_words <= hi + 5:
            score += 0.06

        if re.search(r"\bfind\b|\bprove\b|\bshow that\b|\bif\b.*\bfind\b", lower):
            score += 0.06

        if "(i)" in lower and "(ii)" in lower and n_words > 55:
            score -= 0.05
            flags.append("symmetric_subparts")

        if q.get("human_imperfection") and 18 <= n_words <= 45:
            score += 0.04
        if q.get("sparse_hard") and n_words <= 22:
            score += 0.06
        if q.get("exercise_memory_reuse") and re.search(r"\bfind\b", lower):
            score += 0.03

        sol = score_solution_difficulty(q)
        q.update(sol)
        score = min(1.0, score + sol["solution_difficulty"] * 0.08)

        authenticity = max(0.0, min(1.0, score))
        q["authenticity_score"] = round(authenticity, 3)
        q["authenticity_flags"] = flags
        q["slot_band"] = slot_band
        return q

    @staticmethod
    def _is_one_line_conceptual(stem: str) -> bool:
        low = stem.lower().strip()
        if len(stem.split()) > 18:
            return False
        return bool(
            re.match(
                r"^(can|is|prove|show|find|how many).+\?$",
                low,
                re.I,
            )
            or "can a tangent" in low
        )

    def should_reject(self, q: Dict[str, Any]) -> bool:
        return q.get("authenticity_score", 0) < self.REJECT_THRESHOLD

    def score_batch(
        self, questions: List[Dict[str, Any]], slot_bands: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        for i, q in enumerate(questions):
            band = (slot_bands[i] if slot_bands and i < len(slot_bands) else "L3")
            self.score_question(q, slot_band=band)
        return questions
