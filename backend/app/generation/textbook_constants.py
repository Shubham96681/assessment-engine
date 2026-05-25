"""
Global bans and stem length targets — human textbook behavior (RD / RS).
"""

# Meta language that instantly signals AI worksheets — reject in stems
BANNED_META_PHRASES = (
    "use the diagram",
    "use the figure",
    "show your working",
    "show all working",
    "show complete working",
    "justify briefly",
    "students often",
    "student often",
    "often subtract",
    "often confuse",
    "naive shortcut",
    "wrong shortcut",
    "pedagogical",
    "using theorem",
    "using the theorem",
    "using the tangent",
    "using pythagoras",
    "by pythagoras theorem",
    "hence prove",
    "analyze",
    "analyse",
    "examine",
    "configuration",
    "situation",
    "mechanical-geometric",
    "with reference to",
    "several lines are drawn",
    "study the diagram",
    "explore the",
    "discuss the",
    "treat pq as",
    "lies along the tangent",
    "segment pq lies",
    "identify the right triangle formed",
    "radii are drawn to the points of contact in the diagram",
)

# Over-specification — geometry textbooks assume literacy
BANNED_OVER_SPEC = (
    "touches the circle only at",
    "only at p",
    "only at one point",
    "the segment",
    "lies along",
    "through the centre o meets",
    "in the adjoining figure, a circle has centre",
)

# AI worksheet phrasing (legacy list — kept for compatibility)
AI_WORKSHEET_PHRASES = BANNED_META_PHRASES

# Stem word targets by band (non-FigureBased)
STEM_WORD_TARGETS = {
    "L1": (12, 25),
    "L2": (15, 30),
    "L3": (20, 40),
    "L4": (25, 45),
    "L5": (35, 60),
}

# FigureBased: slightly longer but still compressed vs essay
FIGURE_STEM_WORD_TARGETS = {
    "L1": (20, 35),
    "L2": (25, 45),
    "L3": (30, 50),
    "L4": (35, 55),
    "L5": (40, 60),
}

# Real textbook difficulty mix for 5-question blocks (percent slots)
TEXTBOOK_DIFFICULTY_MIX_5 = [
    {"ui": "easy", "band": "L1"},
    {"ui": "easy", "band": "L2"},
    {"ui": "hard", "band": "L5"},  # spike — uneven
    {"ui": "medium", "band": "L3"},
    {"ui": "hard", "band": "L5"},
]

# Anti-overcompression floor (words) — stem must stay self-contained
MIN_STEM_WORDS = {
    "default": 12,
    "find": 14,
    "prove": 10,
    "figure_based": 14,
}

# When UI difficulty is hard — no L1 spikes; medium floor + HOTS density
HARD_DIFFICULTY_MIX_5 = [
    {"ui": "hard", "band": "L3"},
    {"ui": "hard", "band": "L4"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L3"},
    {"ui": "hard", "band": "L5"},
]

HARD_DIFFICULTY_MIX_8 = [
    {"ui": "hard", "band": "L3"},
    {"ui": "hard", "band": "L4"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L3"},
    {"ui": "hard", "band": "L4"},
    {"ui": "hard", "band": "L3"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
]

# When UI is ~100% hard — every slot L5 (hardest tier; no L3/L4 warm-up)
FULL_HARD_DIFFICULTY_MIX_5 = [
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
]

FULL_HARD_DIFFICULTY_MIX_8 = [
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L5"},
]

TEXTBOOK_DIFFICULTY_MIX_8 = [
    {"ui": "easy", "band": "L1"},
    {"ui": "easy", "band": "L2"},
    {"ui": "hard", "band": "L5"},
    {"ui": "medium", "band": "L3"},
    {"ui": "medium", "band": "L4"},
    {"ui": "easy", "band": "L2"},
    {"ui": "hard", "band": "L5"},
    {"ui": "hard", "band": "L4"},
]
