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
    if "trigonometric" in blob or "trigonometry" in blob:
        return "trigonometry"
    if re.search(r"\b(?:sin|cos|tan|cot|sec|cosec|radian)\b", blob):
        return "trigonometry"
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

# Mixed-independent — standalone stems (no Question 1→2 cross-refs)
_MIXED_INDEPENDENT_CIRCLES_SLOTS: List[Dict[str, Any]] = [
    {
        "stem": (
            "Circles with centres P and Q have radii 5 cm and 3 cm. "
            "If PQ = 10 cm, find the length of the direct common external tangent."
        ),
        "answer": (
            "Given radii 5 cm and 3 cm, PQ = 10 cm. Step 1: Offset along PQ is 2 cm. "
            "Step 2: Tangent length = √(10² − 2²) = √96 cm. Step 3: Radii to contacts are "
            "perpendicular to the tangent. Step 4: Same length from the right trapezoid. "
            "Step 5: Hence the direct common external tangent has length √96 cm."
        ),
        "labels": {"P": "P", "Q": "Q", "R": "R", "S": "S"},
        "positions": {"P": "centre", "Q": "centre", "R": "on_circle", "S": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "P", "to": "Q", "style": "dashed"},
            {"shape": "segment", "from": "R", "to": "S"},
        ],
        "marks": 5,
        "archetype_id": "common_tangent",
    },
    {
        "stem": (
            "From external point T, tangent TA = 9 cm touches a circle at A. "
            "Secant TBC meets the circle at B (nearer T) and C with TB = 4 cm. Find TC."
        ),
        "answer": (
            "Given TA = 9 cm, TB = 4 cm. Step 1: Tangent–secant power gives TA² = TB × TC. "
            "Step 2: 81 = 4 × TC. Step 3: TC = 20.25 cm. Step 4: Check 4 × 20.25 = 81. "
            "Step 5: Hence TC = 20.25 cm."
        ),
        "labels": {"O": "O", "T": "T", "A": "A", "B": "B", "C": "C"},
        "positions": {"O": "centre", "T": "outside", "A": "on_circle", "B": "on_circle", "C": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "A", "style": "dashed"},
            {"shape": "segment", "from": "T", "to": "A"},
            {"shape": "segment", "from": "B", "to": "C"},
        ],
        "marks": 5,
        "archetype_id": "secant_tangent",
    },
    {
        "stem": "Prove that tangents drawn from an external point to a circle are equal in length.",
        "answer": (
            "Given external point X and tangents XY, XZ to a circle with centre O. "
            "Step 1: OY and OZ are radii, so OY = OZ. Step 2: OX is common and "
            "angle OYX = angle OZX = 90°. Step 3: Right triangles OYX and OZX are congruent (RHS). "
            "Step 4: CPCT gives XY = XZ. Step 5: Hence the tangents from X are equal."
        ),
        "labels": {"O": "O", "X": "X", "Y": "Y", "Z": "Z"},
        "positions": {"O": "centre", "X": "outside", "Y": "on_circle", "Z": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "Y", "style": "dashed"},
            {"shape": "segment", "from": "O", "to": "Z", "style": "dashed"},
            {"shape": "segment", "from": "X", "to": "Y"},
            {"shape": "segment", "from": "X", "to": "Z"},
        ],
        "marks": 5,
        "archetype_id": "direct_theorem",
    },
    {
        "stem": (
            "Tangents PM and PN are drawn from P to a circle with centre O and radius 9 cm. "
            "If angle MPN = 52°, find angle MON."
        ),
        "answer": (
            "Given OP bisects angle MPN and radii OM, ON are perpendicular to PM, PN. "
            "Step 1: In quadrilateral OMPN, angle OMP = angle ONP = 90°. Step 2: Angle MPN = 52°. "
            "Step 3: Angle MON = 360° − 90° − 90° − 52° = 128°. Step 4: Central angle equals "
            "the angle between the radii. Step 5: Hence angle MON = 128°."
        ),
        "labels": {"O": "O", "P": "P", "M": "M", "N": "N"},
        "positions": {"O": "centre", "P": "outside", "M": "on_circle", "N": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "M", "style": "dashed"},
            {"shape": "segment", "from": "O", "to": "N", "style": "dashed"},
            {"shape": "segment", "from": "P", "to": "M"},
            {"shape": "segment", "from": "P", "to": "N"},
        ],
        "marks": 6,
        "archetype_id": "angle_theorem",
    },
    {
        "stem": (
            "A circle has centre O and radius 10 cm. Chord CD = 16 cm. "
            "(i) Find OM where M is the midpoint of CD. "
            "(ii) Hence, from E with OE = 13 cm, find the tangent length ET."
        ),
        "answer": (
            "Given radius 10 cm, CD = 16 cm. (i) Step 1: M is midpoint of CD, so CM = 8 cm. "
            "Step 2: OM² = 10² − 8² = 36. Step 3: OM = 6 cm. (ii) Step 4: ET² = OE² − r² = 169 − 100 = 69. "
            "Step 5: Hence ET = √69 cm."
        ),
        "labels": {"O": "O", "C": "C", "D": "D", "M": "M", "E": "E", "T": "T"},
        "positions": {
            "O": "centre",
            "C": "on_circle",
            "D": "on_circle",
            "M": "inside",
            "E": "outside",
            "T": "on_circle",
        },
        "segments": [
            {"shape": "segment", "from": "O", "to": "M", "style": "dashed"},
            {"shape": "segment", "from": "C", "to": "D"},
            {"shape": "segment", "from": "E", "to": "T"},
        ],
        "marks": 7,
        "archetype_id": "hidden_theorem",
    },
    {
        "stem": (
            "From external point U, tangent UV = 12 cm touches a circle at V. "
            "Secant UWX meets the circle at W (nearer U) and X with UW = 5 cm. Find UX."
        ),
        "answer": (
            "Given UV = 12 cm, UW = 5 cm. Step 1: UV² = UW × UX. Step 2: 144 = 5 × UX. "
            "Step 3: UX = 28.8 cm. Step 4: Check 5 × 28.8 = 144. Step 5: Hence UX = 28.8 cm."
        ),
        "labels": {"O": "O", "U": "U", "V": "V", "W": "W", "X": "X"},
        "positions": {"O": "centre", "U": "outside", "V": "on_circle", "W": "on_circle", "X": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "V", "style": "dashed"},
            {"shape": "segment", "from": "U", "to": "V"},
            {"shape": "segment", "from": "W", "to": "X"},
        ],
        "marks": 6,
        "archetype_id": "secant_tangent",
    },
    {
        "stem": (
            "Two tangents PA and PB are drawn to a circle with centre O from P. "
            "If angle APB = 64°, find angle AOB."
        ),
        "answer": (
            "Given angle APB = 64°. Step 1: OA ⟂ PA and OB ⟂ PB. Step 2: In quadrilateral OAPB, "
            "two right angles at A and B. Step 3: angle AOB + angle APB = 180°. Step 4: angle AOB = 116°. "
            "Step 5: Hence angle AOB = 116°."
        ),
        "labels": {"O": "O", "P": "P", "A": "A", "B": "B"},
        "positions": {"O": "centre", "P": "outside", "A": "on_circle", "B": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "A", "style": "dashed"},
            {"shape": "segment", "from": "O", "to": "B", "style": "dashed"},
            {"shape": "segment", "from": "P", "to": "A"},
            {"shape": "segment", "from": "P", "to": "B"},
        ],
        "marks": 6,
        "archetype_id": "angle_theorem",
    },
]

# Board-hard — slot-indexed fallback (0=Q1 … 4=Q5) aligned with chained concentric graph
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
            "In the configuration of Question 1, with PQ = 12 cm from Question 2 touching the outer "
            "circle at Q. (i) Find OP. (ii) Hence point G is 26 cm from O; tangent GH touches the outer "
            "circle at H; secant GJK with GJ = 9 cm. Find GK and verify GH² = GJ × GK."
        ),
        "answer": (
            "From Question 1, outer radius = 17 cm. (i) OP = √(17² + 12²) = √433 cm. "
            "(ii) GH² = 26² − 17² = 387; GK = 387 ÷ 9 = 43 cm. Step 3: GJ × GK = 9 × 43 = 387 = GH². "
            "Hence GK = 43 cm."
        ),
        "labels": {"O": "O", "P": "P", "Q": "Q", "G": "G", "H": "H", "J": "J", "K": "K"},
        "positions": {"O": "centre", "P": "outside", "Q": "on_circle", "G": "outside", "H": "on_circle", "J": "on_circle", "K": "on_circle"},
        "segments": [
            {"shape": "segment", "from": "O", "to": "Q", "style": "dashed"},
            {"shape": "segment", "from": "P", "to": "Q"},
            {"shape": "segment", "from": "G", "to": "H"},
            {"shape": "segment", "from": "J", "to": "K"},
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


def _circles_slot_pool(
    difficulty: str,
    paper_template_id: str = "",
) -> List[Dict[str, Any]]:
    if (paper_template_id or "").strip().lower() == "mixed_independent":
        return _MIXED_INDEPENDENT_CIRCLES_SLOTS
    if (difficulty or "").lower() in ("hard", "difficult"):
        return _CIRCLES_HARD_FIGURE_SLOTS
    return _CIRCLES_FIGURE_SLOTS


def _build_circles_figure(
    slot_index: int,
    difficulty: str,
    bloom: str,
    *,
    paper_template_id: str = "",
) -> Dict[str, Any]:
    pool = _circles_slot_pool(difficulty, paper_template_id)
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
    paper_template_id: str = "",
) -> Dict[str, Any]:
    """Single slot question dict for gap-fill / integrity repair."""
    from app.generation.question_pipeline import finalize_question_dict

    if not paper_template_id:
        try:
            from app.generation.topic_isolation import get_current_topic_state

            paper_template_id = (get_current_topic_state() or {}).get(
                "paper_template_id", ""
            ) or ""
        except Exception:
            paper_template_id = ""

    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    pack = get_chapter_rule_pack(locked_chapter)
    qtype = pack.preferred_type_for_slot(slot_index)
    if qtype == "FigureBased" and locked_chapter == "circles":
        raw = _build_circles_figure(
            slot_index, difficulty, bloom, paper_template_id=paper_template_id
        )
    elif qtype == "FigureBased" and locked_chapter == "quadratic":
        raw = _build_quadratic_figure(slot_index, difficulty, bloom)
    else:
        raw = _build_text_slot_from_pack(
            slot_index,
            locked_chapter=locked_chapter,
            difficulty=difficulty,
            bloom=bloom,
            question_type=qtype,
        )
    return finalize_question_dict(raw)


def _build_text_slot_from_pack(
    slot_index: int,
    *,
    locked_chapter: str,
    difficulty: str,
    bloom: str,
    question_type: str = "LongAnswer",
) -> Dict[str, Any]:
    """Gap-fill / repair slot from ChapterRulePack anchors (not circles FigureBased)."""
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    pack = get_chapter_rule_pack(locked_chapter)
    role = (
        pack.cognitive_blueprint_5[slot_index]
        if slot_index < len(pack.cognitive_blueprint_5)
        else "chapter exercise"
    )
    anchor = (
        pack.embedding_anchors[slot_index]
        if slot_index < len(pack.embedding_anchors)
        else pack.stem_example
    )
    marks = {"easy": 3, "medium": 4, "hard": 5, "difficult": 6}.get(
        (difficulty or "medium").lower(), 4
    )
    arch = (
        pack.archetype_ids[slot_index % len(pack.archetype_ids)]
        if pack.archetype_ids
        else "concept_apply"
    )
    stem = (
        f"{anchor} Use new constants and quadrant labels — not a repeat of prior papers."
    )
    if difficulty in ("hard", "difficult") and question_type == "LongAnswer":
        stem += " (i) Main result. (ii) Hence verify with a numeric check."
    return {
        "id": str(slot_index + 1),
        "type": question_type,
        "question": stem,
        "marks": marks,
        "correct_answer": (
            f"Given → Step 1 → Step 2 → Hence ({role}; match {pack.display_title} style)."
        ),
        "explanation": f"{bloom}-level {pack.chapter_key} gap-fill from pack anchor.",
        "archetype_id": arch,
    }


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
