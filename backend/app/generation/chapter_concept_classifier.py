"""

Chapter concept classifier — lock generation to content extracted from the uploaded PDF.



No NCERT chapter-number tables. Filename is a weak hint; PDF body text is primary.

"""

from __future__ import annotations



import re

from typing import Dict, List, Optional, Tuple



# Linguistic signals in PDF text (not chapter-number maps)

_CONCEPT_PATTERNS: List[Tuple[str, str, float]] = [

    (r"\bquadratic\s+equation|\bdiscriminant\b|nature\s+of\s+roots|x\^2|x²|equal\s+roots", "quadratic", 3.0),

    (r"\bform\s+the\s+quadratic|\b2x²|\bax²\s*\+\s*bx", "quadratic", 2.5),

    (r"\barea\s+is\s+\d+.*\b(?:breadth|length|width)|length\s+is\s+(?:twice|2\s*times).*breadth", "quadratic", 2.0),

    (r"\btangent|\bsecant|\bconcentric\s+circle|\bradius\b|\bpoint\s+of\s+contact", "circles", 3.0),

    (r"\bexternal\s+point.*tangent|tangents?\s+[A-Z][A-Z].*circle", "circles", 2.5),

    (r"\bparallelogram|\brhombus|\btrapezium|\btrapezoid|\bmidpoint\s+theorem", "quadrilaterals", 3.0),

    (r"\bcyclic\s+quadrilateral|opposite\s+angles.*supplementary|diagonals?\s+of\s+.*parallelogram", "quadrilaterals", 2.5),

    (r"\bdiagonal.*bisect|prove.*parallelogram", "quadrilaterals", 2.0),

    (r"\bsimilar\s+triangles|\bcongruence|\bpythagoras", "triangles", 2.0),

    (r"\barithmetic\s+progression|\bcommon\s+difference|\bnth\s+term", "arithmetic", 2.0),
    (r"\bpolynomial|\bfactor(?:ise|ize)|remainder\s+theorem|\bzeroes?\s+of", "polynomials", 2.5),
    (r"\bcoordinate\s+geometry|\bslope\s+of|\bdistance\s+formula|\bsection\s+formula", "coordinate_geometry", 2.5),
    (r"\bmean\s+median\s+mode|\bfrequency\s+distribution|\bstatistics|\bhistogram", "statistics", 2.0),
    (r"\bprobability|\bmutually\s+exclusive|\brandom\s+experiment", "probability", 2.5),
    (r"\breal\s+numbers|\beuclid|hcf|lcm|\birrational|\bprime\s+factor", "real_numbers", 2.0),
    (r"\bsimilarity\s+of\s+triangles|\bareas?\s+related\s+to\s+circles|\bsector\s+area", "mensuration", 2.0),
    (r"\bsurface\s+area|\bvolume\s+of|\bcone|\bcylinder|\bsphere", "surface_volume", 2.5),
    (r"\blinear\s+equation|\bpair\s+of\s+linear", "linear_equations", 2.0),

    (

        r"\btrigonometric\s+function|\btrigonometric\s+identity|"

        r"\bsin\s*[\(\sx]|\bcos\s*[\(\sx]|\btan\s*[\(\sx]|"

        r"\bcot\s*[\(\sx]|\bsec\s*[\(\sx]|\bcosec|"

        r"\bradian\s+measure|\bdegree\s+measure|"

        r"angle\s+of\s+elevation|standard\s+angle",

        "trigonometry",

        3.0,

    ),

]





def _score_text_for_chapters(text: str) -> Dict[str, float]:

    low = (text or "").lower()

    scores: Dict[str, float] = {}

    for pattern, chapter, weight in _CONCEPT_PATTERNS:

        if re.search(pattern, low, re.I):

            scores[chapter] = scores.get(chapter, 0) + weight

    return scores





def resolve_locked_chapter(

    *,

    filename: str = "",

    topic_focus: str = "",

    context: str = "",

) -> Tuple[str, str, float]:

    """

    Authoritative chapter from PDF content (+ optional user topic_focus).

    """

    from app.generation.pdf_content_analyzer import infer_locked_chapter_from_pdf



    return infer_locked_chapter_from_pdf(
        blob=context or "",
        filename=filename or "",
        topic_focus=topic_focus or "",
        subtopics=None,
    )





def refine_locked_chapter(

    chapter: str,

    source: str,

    confidence: float,

    *,

    filename: str = "",

    context: str = "",

    subtopics: Optional[List[str]] = None,

) -> Tuple[str, str, float]:

    """Re-score using full PDF blob + subtopics; override only if content strongly disagrees."""

    from app.generation.pdf_content_analyzer import infer_locked_chapter_from_pdf



    blob = "\n".join([context or "", " ".join(subtopics or [])])

    pdf_ch, pdf_src, pdf_conf = infer_locked_chapter_from_pdf(

        blob=blob,

        filename=filename,

        topic_focus="",

    )

    if pdf_ch == "generic":

        return chapter, source, confidence

    if chapter == "generic" or pdf_conf > confidence + 0.12:

        return pdf_ch, pdf_src, pdf_conf

    if pdf_ch != chapter and pdf_conf >= 0.55:

        return pdf_ch, pdf_src, pdf_conf

    return chapter, source, confidence





def classify_stem_chapter(stem: str) -> Tuple[str, float, Dict[str, float]]:

    """Infer chapter from question stem only."""

    scores = _score_text_for_chapters(stem)

    if not scores:

        return "generic", 0.0, scores

    best = max(scores, key=scores.get)

    total = sum(scores.values()) or 1

    return best, scores[best] / total, scores





def stem_matches_locked_chapter(stem: str, locked_chapter: str) -> Tuple[bool, str]:

    if locked_chapter in ("generic", ""):

        return True, ""

    detected, conf, _ = classify_stem_chapter(stem)

    if detected == "generic" or conf < 0.25:

        return True, ""

    if detected == locked_chapter:

        return True, ""

    return False, f"stem_chapter_mismatch:{detected}_vs_{locked_chapter}"





def context_supports_chapter(context: str, locked_chapter: str, min_score: float = 1.0) -> bool:

    scores = _score_text_for_chapters(context[:4000])

    if locked_chapter not in scores:

        return locked_chapter == "generic"

    return scores.get(locked_chapter, 0) >= min_score


