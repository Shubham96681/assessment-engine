"""
Prompt-driven local question generation (no cloud API key).
Builds structured JSON when cloud/Ollama/RAG agent are unavailable.
Uses per-slot templates so fallback never emits five copies of one stem.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


def _clean_text(text: str) -> str:
    text = re.sub(r"Reprint\s+\d{4}-\d{2}", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,4}\s+MATHEMATICS\b", " ", text, flags=re.I)
    text = re.sub(r"\bActivity\s+\d+\s*:", " ", text, flags=re.I)
    text = re.sub(r"-{2,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _detect_chapter(context: str, filename: str = "") -> str:
    blob = f"{filename} {context}".lower()
    if "quadratic" in blob or "discriminant" in blob or "x²" in blob or "x^2" in blob:
        return "quadratic"
    if "circle" in blob or "tangent" in blob or "secant" in blob:
        return "circles"
    if "quadrilateral" in blob or "parallelogram" in blob:
        return "quadrilaterals"
    return "generic"


def _figure_spec_circle(
    labels: Dict[str, str],
    *,
    show_concentric: bool = False,
    positions: Optional[Dict[str, str]] = None,
    inner_radius_ratio: float = 0.55,
) -> Dict[str, Any]:
    """Build figure_spec with every A–Z point in labels; positions override defaults."""
    o = labels.get("O", "O")
    pos_map = {k.upper(): v for k, v in (positions or {}).items()}
    elements: List[Dict[str, Any]] = [
        {"shape": "circle", "label": "Circle"},
        {"shape": "point", "label": o, "position": "centre"},
    ]
    for key, val in labels.items():
        if len(key) != 1 or not key.isalpha() or key.upper() == o.upper():
            continue
        letter = key.upper()
        pos = pos_map.get(letter)
        if not pos:
            pos = (
                "outside"
                if letter in ("F", "J", "K", "N", "L", "U", "P")
                else "on_circle"
            )
        elements.append({"shape": "point", "label": letter, "position": pos})
    for seg in labels.get("segments", []):
        elements.append(seg)
    if show_concentric:
        elements.append(
            {"shape": "circle", "label": "inner", "radius_ratio": inner_radius_ratio}
        )
    label_map = {k.upper(): v for k, v in labels.items() if len(k) == 1 and k.isalpha()}
    return {
        "type": "labeled_diagram",
        "title": "Diagram",
        "elements": elements,
        "show_right_angle": labels.get("show_right_angle", True),
        "labels": label_map,
    }


# Each entry: (stem, answer, figure labels dict, marks)
_CIRCLES_FIGURE_SLOTS: List[Dict[str, Any]] = [
    {
        "stem": (
            "From external point K, tangents KX and KY touch a circle with centre O "
            "at X and Y. Radii OX and OY are drawn. If angle XOY = 92°, find angle XKY "
            "between the tangents."
        ),
        "answer": (
            "Given tangents from K, angle XOY = 92°. Step 1: OX ⟂ KX and OY ⟂ KY. "
            "Step 2: In quadrilateral OXKY, angles at X and Y are 90°. "
            "Step 3: angle XOY + angle XKY = 180°. Hence angle XKY = 88°."
        ),
        "labels": {"O": "O", "K": "K", "X": "X", "Y": "Y"},
        "positions": {"O": "centre", "K": "outside", "X": "on_circle", "Y": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "X", "style": "dashed"},
            {"shape": "segment", "from": "O", "to": "Y", "style": "dashed"},
            {"shape": "segment", "from": "K", "to": "X"},
            {"shape": "segment", "from": "K", "to": "Y"},
        ],
        "marks": 4,
    },
    {
        "stem": (
            "Tangents UC and UD are drawn to a circle with centre O from point U, "
            "touching at C and D. Chord CD is drawn. If angle COD = 68°, find angle CUD."
        ),
        "answer": (
            "Given UC = UD. Step 1: OC ⟂ UC, OD ⟂ UD. Step 2: angle COD + angle CUD = 180°. "
            "Step 3: angle CUD = 180° − 68° = 112°. Hence angle between tangents is 112°."
        ),
        "labels": {"O": "O", "U": "U", "C": "C", "D": "D"},
        "positions": {"O": "centre", "U": "outside", "C": "on_circle", "D": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "C", "style": "dashed"},
            {"shape": "segment", "from": "O", "to": "D", "style": "dashed"},
            {"shape": "segment", "from": "C", "to": "D"},
            {"shape": "segment", "from": "U", "to": "C"},
            {"shape": "segment", "from": "U", "to": "D"},
        ],
        "marks": 5,
    },
    {
        "stem": (
            "Two concentric circles have centre O and radii 11 cm and 7 cm. "
            "A chord EF of the larger circle touches the smaller circle at G. Find the length EF."
        ),
        "answer": (
            "Given R = 11 cm, r = 7 cm. Step 1: OG ⟂ EF (radius ⟂ tangent). "
            "Step 2: OG bisects chord EF, so EG = GF. Step 3: In right triangle OEG, "
            "EG = √(11² − 7²) = √48 = 4√3 cm. Step 4: EF = 2 × 4√3 = 8√3 cm. Hence EF = 8√3 cm."
        ),
        "labels": {"O": "O", "E": "E", "F": "F", "G": "G"},
        "positions": {"O": "centre", "E": "on_circle", "F": "on_circle", "G": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "G", "style": "dashed"},
            {"shape": "segment", "from": "E", "to": "F"},
        ],
        "concentric": True,
        "inner_radius_ratio": 7 / 11,
        "marks": 5,
    },
    {
        "stem": (
            "From N, tangent NP = 14 cm touches a circle at P. Secant NQS meets the circle "
            "at Q and S with NQ = 9 cm. Find NS using the tangent–secant relation from the chapter."
        ),
        "answer": (
            "Given NP = 14, NQ = 9. Step 1: NP² = NQ × NS. Step 2: 196 = 9 × NS. "
            "Step 3: NS = 196/9 ≈ 21.78 cm. Step 4: QS = NS − NQ. Hence NS = 196/9 cm."
        ),
        "labels": {"O": "O", "N": "N", "P": "P", "Q": "Q", "S": "S"},
        "positions": {"O": "centre", "N": "outside", "P": "on_circle", "Q": "on_circle", "S": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "N", "to": "P"},
            {"shape": "segment", "from": "N", "to": "Q"},
            {"shape": "segment", "from": "Q", "to": "S"},
        ],
        "marks": 4,
    },
    {
        "stem": (
            "From J, tangents JA and JB touch a circle with centre O and radius 8 cm. "
            "If OJ = 17 cm, find each tangent length. **OR** If angle AOB = 124°, find angle AJB."
        ),
        "answer": (
            "Given r = 8, OJ = 17. Step 1: JA² = 17² − 8² = 225. Step 2: JA = JB = 15 cm. "
            "OR: angle AJB = 180° − 124° = 56°. Hence tangent length 15 cm or angle 56°."
        ),
        "labels": {"O": "O", "J": "J", "A": "A", "B": "B"},
        "positions": {"O": "centre", "J": "outside", "A": "on_circle", "B": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "A", "style": "dashed"},
            {"shape": "segment", "from": "O", "to": "B", "style": "dashed"},
            {"shape": "segment", "from": "J", "to": "A"},
            {"shape": "segment", "from": "J", "to": "B"},
        ],
        "marks": 6,
    },
]

# Board-hard — slot-indexed fallback (0=Q1 … 4=Q5) aligned with paper dependency graph
_CIRCLES_HARD_FIGURE_SLOTS: List[Dict[str, Any]] = [
    {
        "stem": (
            "Two concentric circles have centre O and radii 17 cm and 8 cm. "
            "A chord AB of the larger circle touches the smaller circle at T. Find AB."
        ),
        "answer": (
            "Given R = 17 cm, r = 8 cm. Step 1: OT is perpendicular to AB at T. "
            "Step 2: T bisects AB. Step 3: AT = 15 cm. Step 4: AB = 30 cm. Hence AB = 30 cm."
        ),
        "labels": {"O": "O", "A": "A", "B": "B", "T": "T"},
        "positions": {"O": "centre", "A": "on_circle", "B": "on_circle", "T": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "T", "style": "dashed"},
            {"shape": "segment", "from": "A", "to": "B"},
        ],
        "concentric": True,
        "inner_radius_ratio": 8 / 17,
        "marks": 5,
        "archetype_id": "concentric",
    },
    {
        "stem": (
            "In the same concentric circles as in Question 1. Hence, from external point P, "
            "tangent PQ = 12 cm touches the outer circle at Q, and secant PRT meets the circle at "
            "R (nearer P) and T with PR = 4 cm. Find RT and verify PQ² = PR × PT."
        ),
        "answer": (
            "From Question 1, OQ = 17 cm. Step 1: PQ² = PR × PT. Step 2: 144 = 4(4 + RT). "
            "Step 3: RT = 32 cm. Step 4: PR × PT = 144. Hence RT = 32 cm."
        ),
        "labels": {"O": "O", "P": "P", "Q": "Q", "R": "R", "T": "T"},
        "positions": {"O": "centre", "P": "outside", "Q": "on_circle", "R": "on_circle", "T": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "Q", "style": "dashed"},
            {"shape": "segment", "from": "P", "to": "Q"},
            {"shape": "segment", "from": "R", "to": "T"},
        ],
        "concentric": True,
        "inner_radius_ratio": 8 / 17,
        "marks": 6,
        "archetype_id": "secant_tangent",
    },
    {
        "stem": (
            "In a circle with centre O, a line through point S on the circle meets the circle only at S. "
            "Given that OS is perpendicular to this line at S, prove that the line is tangent to the circle at S."
        ),
        "answer": (
            "Given OS perpendicular to the line at S and the line meets the circle only at S. "
            "Step 1: Suppose a second intersection X exists. Step 2: OS perpendicular to the line forces "
            "OX < OS, so X is inside the circle — impossible. Step 3: Hence the line is tangent at S."
        ),
        "labels": {"O": "O", "S": "S", "A": "A"},
        "positions": {"O": "centre", "S": "on_circle", "A": "outside"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "S", "style": "dashed"},
            {"shape": "segment", "from": "S", "to": "A"},
        ],
        "marks": 6,
        "archetype_id": "chord_tangent",
    },
    {
        "stem": (
            "Circles with centres G and H have radii 3 cm and 8 cm respectively. If GH = 13 cm, "
            "find the length of a direct common external tangent EF and the acute angle between EF and GH "
            "(give the angle as sin inverse of the appropriate ratio)."
        ),
        "answer": (
            "Step 1: EF = 12 cm from 13² − 5². Step 2: sin θ = 5/13. Hence EF = 12 cm and θ = sin inverse (5/13)."
        ),
        "labels": {"G": "G", "H": "H", "E": "E", "F": "F"},
        "positions": {"G": "centre", "H": "centre", "E": "on_circle", "F": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "G", "to": "H", "style": "dashed"},
            {"shape": "segment", "from": "E", "to": "F"},
        ],
        "marks": 6,
        "archetype_id": "common_tangent",
    },
    {
        "stem": (
            "Using the outer circle from Question 1 and the tangent-secant at P from Question 2 "
            "(PQ = 12 cm, PR = 4 cm). (i) Find OP. (ii) Hence, from point W with OW = 23 cm, find the "
            "tangent length WU to the outer circle; if a secant through W meets the circle at X (nearer) "
            "and Y with WX = 8 cm, find WY and verify WU² = WX × WY."
        ),
        "answer": (
            "From Question 1, OQ = 17 cm. From Question 2, PQ = 12 cm. (i) OP = sqrt(433) cm. "
            "(ii) WU = sqrt(240) cm, WY = 30 cm, check 8 × 30 = 240."
        ),
        "labels": {"O": "O", "P": "P", "Q": "Q", "W": "W", "U": "U", "X": "X", "Y": "Y"},
        "positions": {"O": "centre", "P": "outside", "Q": "on_circle", "W": "outside", "U": "on_circle", "X": "on_circle", "Y": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "Q", "style": "dashed"},
            {"shape": "segment", "from": "P", "to": "Q"},
            {"shape": "segment", "from": "W", "to": "X"},
            {"shape": "segment", "from": "X", "to": "Y"},
        ],
        "marks": 7,
        "archetype_id": "hidden_theorem",
    },
]

_QUADRATIC_FIGURE_SLOTS: List[Dict[str, Any]] = [
    {
        "stem": "Solve 5x² − 11x + 6 = 0 by factorisation and verify one root by substitution.",
        "answer": "Step 1: 5x² − 11x + 6 = (5x − 6)(x − 1) = 0. Step 2: x = 6/5 or x = 1. Step 3: Check x = 1: 5 − 11 + 6 = 0. Hence roots 1 and 6/5.",
        "marks": 4,
        "table": True,
    },
    {
        "stem": "Find the discriminant of 3x² + 4x − 9 = 0 and state the nature of its roots.",
        "answer": "D = 16 + 108 = 124 > 0. Hence two distinct real roots.",
        "marks": 4,
        "table": True,
    },
    {
        "stem": "Find k if 2x² + kx + 18 = 0 has equal real roots.",
        "answer": "D = k² − 144 = 0 ⇒ k = ±12. Common root x = −k/4.",
        "marks": 5,
        "table": True,
    },
    {
        "stem": (
            "A rectangular plot has length (2x + 3) m and breadth x m. Its area is 540 m². "
            "Form a quadratic in x and find the breadth."
        ),
        "answer": "2x² + 3x − 540 = 0 ⇒ (2x + 27)(x − 20) = 0. Reject x = −13.5; breadth x = 20 m.",
        "marks": 5,
    },
    {
        "stem": (
            "Two consecutive positive integers have sum of squares 365. "
            "Form the quadratic and find the integers."
        ),
        "answer": "n² + (n+1)² = 365 ⇒ 2n² + 2n − 364 = 0 ⇒ n = 13. Integers 13 and 14.",
        "marks": 6,
    },
]


def _build_circles_figure(slot_index: int, difficulty: str, bloom: str) -> Dict[str, Any]:
    pool = (
        _CIRCLES_HARD_FIGURE_SLOTS
        if (difficulty or "").lower() in ("hard", "difficult")
        else _CIRCLES_FIGURE_SLOTS
    )
    tpl = pool[slot_index % len(pool)]
    labels = dict(tpl.get("labels", {}))
    segs = list(tpl.get("segments", []))
    spec = _figure_spec_circle(
        labels,
        show_concentric=tpl.get("concentric", False),
        positions=tpl.get("positions"),
        inner_radius_ratio=float(tpl.get("inner_radius_ratio", 0.55)),
    )
    spec["elements"].extend(segs)
    marks = tpl.get("marks", 5)
    if difficulty == "hard":
        marks = max(marks, 5)
    return {
        "id": str(slot_index + 1),
        "type": "FigureBased",
        "question": tpl["stem"],
        "marks": marks,
        "figure_type": "labeled_diagram",
        "figure_spec": spec,
        "correct_answer": tpl["answer"],
        "explanation": f"{bloom}-level circles item (slot template {slot_index + 1}).",
        "archetype_id": tpl.get(
            "archetype_id",
            ["concentric", "secant_tangent", "chord_tangent", "common_tangent", "hidden_theorem"][
                slot_index % 5
            ],
        ),
    }


def _build_quadratic_figure(slot_index: int, difficulty: str, bloom: str) -> Dict[str, Any]:
    tpl = _QUADRATIC_FIGURE_SLOTS[slot_index % len(_QUADRATIC_FIGURE_SLOTS)]
    spec: Dict[str, Any] = {
        "type": "table" if tpl.get("table") else "labeled_diagram",
        "title": "Diagram",
        "elements": [],
        "labels": {},
    }
    if tpl.get("table"):
        spec["headers"] = ["Item", "Value"]
        spec["rows"] = [["equation", "see stem"], ["task", "solve"]]
    marks = tpl.get("marks", 4)
    if difficulty == "hard":
        marks = max(marks, 5)
    return {
        "id": str(slot_index + 1),
        "type": "FigureBased",
        "question": tpl["stem"],
        "marks": marks,
        "figure_type": spec["type"],
        "figure_spec": spec,
        "correct_answer": tpl["answer"],
        "explanation": f"{bloom}-level quadratic item (slot template {slot_index + 1}).",
    }


def build_local_response(
    context: str,
    task: Dict[str, Any],
    *,
    slot_offset: int = 0,
    locked_chapter: str = "",
    filename: str = "",
) -> str:
    qtype = task["type"].value if hasattr(task["type"], "value") else str(task["type"])
    difficulty = task.get("difficulty", "medium")
    bloom = task["bloom_level"].value if hasattr(task["bloom_level"], "value") else str(
        task.get("bloom_level", "Apply")
    )
    n = max(1, task.get("count", 1))
    chapter = locked_chapter or _detect_chapter(context, filename)
    items: List[Dict[str, Any]] = []

    for i in range(n):
        slot_idx = slot_offset + i
        if qtype == "FigureBased" and chapter == "circles":
            items.append(_build_circles_figure(slot_idx, difficulty, bloom))
        elif qtype == "FigureBased" and chapter == "quadratic":
            items.append(_build_quadratic_figure(slot_idx, difficulty, bloom))
        elif qtype == "FigureBased":
            items.append(_build_circles_figure(slot_idx, difficulty, bloom))
        elif qtype == "MCQ":
            items.append(_mcq_item("the chapter topic", difficulty, _numeric_givens(slot_idx), slot_idx))
        elif qtype == "TrueFalse":
            items.append(_true_false_item("circle geometry", _numeric_givens(slot_idx), slot_idx))
        elif qtype == "LongAnswer":
            items.append(_long_item("the chapter", difficulty, _numeric_givens(slot_idx), slot_idx))
        else:
            items.append(_short_item("the chapter", difficulty, bloom, _numeric_givens(slot_idx), slot_idx))

    return json.dumps(items, ensure_ascii=False)


def local_slot_question_dict(
    slot_index: int,
    *,
    locked_chapter: str = "circles",
    difficulty: str = "medium",
    bloom: str = "Apply",
) -> Dict[str, Any]:
    """Single slot question dict for gap-fill / integrity repair."""
    from app.generation.question_pipeline import finalize_question_dict

    if locked_chapter == "circles":
        raw = _build_circles_figure(slot_index, difficulty, bloom)
    elif locked_chapter == "quadratic":
        raw = _build_quadratic_figure(slot_index, difficulty, bloom)
    else:
        raw = _build_circles_figure(slot_index, difficulty, bloom)
    return finalize_question_dict(raw)


def build_local_slot_response(
    context: str,
    task: Dict[str, Any],
    slot_index: int,
    *,
    locked_chapter: str = "",
    filename: str = "",
) -> str:
    """One JSON object for quality-regen fallback — unique per slot_index."""
    task_one = {**task, "count": 1}
    raw = build_local_response(
        context,
        task_one,
        slot_offset=slot_index,
        locked_chapter=locked_chapter,
        filename=filename,
    )
    try:
        items = json.loads(raw)
        if items:
            items[0]["id"] = str(slot_index + 1)
            return json.dumps(items[:1], ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    return raw


def _numeric_givens(i: int) -> Dict[str, int]:
    base = 3 + (i % 7)
    return {"a": base, "b": base + 2, "c": base * base}


def _mcq_item(topic: str, difficulty: str, nums: Dict[str, int], i: int) -> Dict[str, Any]:
    a, b, c = nums["a"], nums["b"], nums["c"]
    correct_val = c - a * b if difficulty != "hard" else (a + b) ** 2 - c
    stem = (
        f"For {topic}, with a = {a} and b = {b}, which value equals the simplified result "
        f"after applying the chapter relation (not the intermediate product a × b)?"
    )
    wrong1, wrong2, wrong3 = correct_val + a, correct_val - b, a * b
    opts = [
        {"label": "A", "text": str(wrong1), "is_correct": False},
        {"label": "B", "text": str(correct_val), "is_correct": True},
        {"label": "C", "text": str(wrong2), "is_correct": False},
        {"label": "D", "text": str(wrong3), "is_correct": False},
    ]
    return {
        "id": str(i + 1),
        "type": "MCQ",
        "question": stem,
        "marks": 1,
        "options": opts,
        "correct_answer": "B",
        "explanation": f"Two-step {topic} calculation; option B is correct.",
    }


def _short_item(topic: str, difficulty: str, bloom: str, nums: Dict[str, int], i: int) -> Dict[str, Any]:
    a, b, c = nums["a"], nums["b"], nums["c"]
    marks = {"easy": 2, "medium": 3, "hard": 4}.get(difficulty, 3)
    q = (
        f"({bloom}) If x = {a} and y = {b}, show that (x + y)² − 4xy = (x − y)². "
        f"Hence evaluate when x − y = {c - a}."
    )
    if difficulty == "hard":
        q += f"\nOR\nState when equality holds in (x + y)² ≥ 4xy."
    return {
        "id": str(i + 1),
        "type": "ShortAnswer",
        "question": q,
        "marks": marks,
        "correct_answer": (
            f"(x+y)² − 4xy = (x−y)²; with x−y = {c - a}, value = {(c - a) ** 2}."
        ),
        "explanation": "Algebra identity — multi-step.",
    }


def _long_item(topic: str, difficulty: str, nums: Dict[str, int], i: int) -> Dict[str, Any]:
    a, b = nums["a"], nums["b"]
    return {
        "id": str(i + 1),
        "type": "LongAnswer",
        "question": (
            f"({topic}) (i) Prove the main result for general positive integers m, n.\n"
            f"(ii) Verify for m = {a}, n = {b}.\n"
            f"(iii) Hence find one related quantity.\n"
            f"OR\n(i) Solve a standard problem with a = {a}, b = {b}."
        ),
        "marks": 5,
        "correct_answer": "Proof (i); numeric check (ii); application (iii) with Hence.",
        "explanation": "Long answer with sub-parts.",
    }


def _true_false_item(topic: str, nums: Dict[str, int], i: int) -> Dict[str, Any]:
    a, b = nums["a"], nums["b"]
    is_true = i % 2 == 0
    if is_true:
        stmt = (
            f"Tangents from an external point to a circle are equal in length "
            f"for the {topic} configuration with radius {a} cm."
        )
        ans = "True"
    else:
        stmt = (
            f"The distance from centre to external point equals the tangent length "
            f"when radius is {a} cm and tangent is {b} cm (without Pythagoras)."
        )
        ans = "False"
    return {
        "id": str(i + 1),
        "type": "TrueFalse",
        "question": stmt,
        "marks": 1,
        "correct_answer": ans,
        "explanation": "Theorem vs misconception.",
    }
