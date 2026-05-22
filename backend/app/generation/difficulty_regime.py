"""
Difficulty regimes — separate board textbook hardness from olympiad-style compression.

UI 'hard' on Class 10 board track → board_hard (RD/RS depth, not L5 olympiad stacking).
"""
from __future__ import annotations

from typing import Tuple

BOARD_HARD = "board_hard"
BOARD_MEDIUM = "board_medium"
BOARD_EASY = "board_easy"
OLYMPIAD_INTRO = "olympiad_intro"
OLYMPIAD_FULL = "olympiad_full"


def resolve_difficulty_regime(
    ui_difficulty: str,
    *,
    exam_track: str = "board",
    class_level: str = "10",
) -> str:
    ui = (ui_difficulty or "medium").lower()
    track = (exam_track or "board").lower()
    cls = (class_level or "10").lower()

    if track in ("jee_mains", "jee_advanced", "jee"):
        if ui in ("hard", "difficult"):
            return OLYMPIAD_INTRO if "10" in cls or "9" in cls else OLYMPIAD_FULL
        return BOARD_MEDIUM

    if ui in ("hard", "difficult"):
        return BOARD_HARD
    if ui in ("easy",):
        return BOARD_EASY
    return BOARD_MEDIUM


def regime_calibration_lines(regime: str, chapter: str) -> Tuple[str, ...]:
    """Short, non-duplicated difficulty guidance for the compiler."""
    ch = (chapter or "generic").strip().lower()
    if regime == BOARD_HARD:
        if ch == "circles":
            return (
                "REGIME: board_hard — NCERT/RD Sharma Class 10 Circles depth.",
                "Target 3–5 inference steps per L4/L5 item; ONE sparse proof slot; no olympiad fusion.",
                "HOTS = disguised reuse + OR with separate givens — not unnamed advanced theorems.",
            )
        if ch == "quadratic":
            return (
                "REGIME: board_hard — discriminant, parameter k, word models; no geometry.",
                "L4/L5: form → D or factor → roots → verify (3+ steps).",
            )
        return (
            "REGIME: board_hard — textbook exercise depth from SOURCE.",
            "L4/L5: 3+ dependent steps; traps invisible in stem.",
        )
    if regime in (OLYMPIAD_INTRO, OLYMPIAD_FULL):
        return (
            f"REGIME: {regime} — multi-theorem chains allowed; still chapter-locked vocabulary.",
            "Sparse stems permitted on L5; proofs may chain 5+ steps.",
        )
    if regime == BOARD_EASY:
        return ("REGIME: board_easy — direct application, 2–3 steps.",)
    return ("REGIME: board_medium — standard exercise mix (~2 medium, ~1 challenge).",)
