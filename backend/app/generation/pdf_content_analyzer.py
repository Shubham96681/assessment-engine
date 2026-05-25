"""
PDF-driven topic / chapter / theorem extraction — no NCERT chapter-number tables.

All signals come from indexed chunk text + optional user topic_focus.
Filename tokens are weak hints only (same lexicons as body text).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.chapter_concept_classifier import _score_text_for_chapters

# ── Theorem / result lines in textbooks ─────────────────────────────────────
_THEOREM_HEADING = re.compile(
    r"(?im)^\s*(?:theorem|lemma|corollary|postulate|result|property)\s*"
    r"([\d.]+)?\s*[:\.\-–]?\s*(.{8,140}?)(?:\n|$)",
)
_THEOREM_NAMED = re.compile(
    r"(?im)\b("
    r"(?:basic\s+proportionality|pythagoras|thales|mid[\s\-]?point|"
    r"angle\s+sum|factor|remainder|distance|section|tangent[\s\-]?radius|"
    r"secant[\s\-]?tangent|cyclic|similar\s+triangles|"
    r"pythagorean\s+identity|trigonometric\s+identity)"
    r"\s+theorem)\b",
)
_PROVE_BLOCK = re.compile(
    r"(?im)\b(?:prove|show)\s+that\s+([^\n.;]{12,100})",
)
_CHAPTER_TITLE = re.compile(
    r"(?im)(?:^|\n)\s*chapter\s+[\divxlcdm\d]+\s*"
    r"[:.\-–]?\s*([^\n]{4,80})",
)
_EXERCISE_LINE = re.compile(
    r"(?im)^\s*(?:exercise|example)\s+([\d.]+)\s*",
)
_EXERCISE_ITEM = re.compile(
    r"(?im)^\s*(\d{1,2})[\.\)]\s+([A-Za-z][^\n]{8,90})",
)
_FORMULA_IDENTITY = re.compile(
    r"(?im)\b(?:identity|formula)\s*[:\-]?\s*([^\n]{8,80})",
)


def _slug_id(text: str, prefix: str = "thm") -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:48]
    if not s:
        s = hashlib.sha256((text or "").encode()).hexdigest()[:10]
    return f"{prefix}_{s}"[:56]


def _chapter_lexicons() -> Dict[str, Tuple[str, ...]]:
    """Build scoring lexicons from rule packs (data-driven, not NCERT tables)."""
    from app.generation.chapter_rule_packs import CHAPTER_RULES

    lex: Dict[str, Tuple[str, ...]] = {}
    for key, pack in CHAPTER_RULES.items():
        terms: List[str] = [
            pack.display_title.lower(),
            pack.chapter_key,
            *pack.retrieval_semantic_terms,
            *pack.archetype_ids,
        ]
        seen: set[str] = set()
        clean: List[str] = []
        for t in terms:
            t = (t or "").strip().lower()
            if t and t not in seen and len(t) > 2:
                seen.add(t)
                clean.append(t)
        lex[key] = tuple(clean)
    return lex


def score_chapters_from_text(text: str) -> Dict[str, float]:
    """Lexicon + concept-pattern scores on PDF body."""
    scores = dict(_score_text_for_chapters(text or ""))
    low = (text or "").lower()
    for chapter, terms in _chapter_lexicons().items():
        for term in terms:
            if len(term) <= 3:
                if re.search(rf"\b{re.escape(term)}\b", low):
                    scores[chapter] = scores.get(chapter, 0) + 0.4
            elif term in low:
                scores[chapter] = scores.get(chapter, 0) + 0.6
    return scores


def score_chapters_from_filename(filename: str) -> Dict[str, float]:
    """Score filename tokens against the same lexicons as PDF body text."""
    stem = re.sub(r"[_\.\-]+", " ", (filename or "").rsplit(".", 1)[0].lower())
    if not stem.strip():
        return {}
    return score_chapters_from_text(stem)


def _filename_names_chapter_explicitly(filename: str) -> bool:
    """Filename like Chapter_3_Trigonometric_Functions — trust name over stray PDF lines."""
    low = (filename or "").lower()
    return bool(
        re.search(
            r"trigonometric|trigonometry|quadratic|polynomial|"
            r"quadrilateral|parallelogram|probability|statistics|"
            r"coordinate|arithmetic|\bcircles\b|\btriangles\b",
            low,
        )
    )


def dominant_chapter_from_text(text: str) -> Optional[Tuple[str, float]]:
    """Best chapter if one domain clearly leads (e.g. subtopics all sin/cos)."""
    scores = score_chapters_from_text(text or "")
    if not scores:
        return None
    ordered = sorted(scores.items(), key=lambda x: -x[1])
    best_ch, best_sc = ordered[0]
    if len(ordered) < 2:
        return best_ch, best_sc
    second_sc = ordered[1][1]
    if best_sc >= second_sc * 1.35 and best_sc >= 2.0:
        return best_ch, best_sc
    return None


_TRIG_SIGNAL_RE = re.compile(
    r"\b(?:sin|cos|tan|cot|sec|cosec|radian|trigonometric|degree\s+measure)\b",
    re.I,
)
_GEO_CIRCLE_SIGNAL_RE = re.compile(
    r"\b(?:circle|chord|secant|tangent|radius|diameter)\b",
    re.I,
)


def infer_locked_chapter_from_pdf(
    *,
    blob: str = "",
    filename: str = "",
    topic_focus: str = "",
    subtopics: Optional[List[str]] = None,
) -> Tuple[str, str, float]:
    """
    Pick chapter from PDF content first; filename is a low-weight tie-breaker.
    Explicit filenames (e.g. Trigonometric_Functions) override stray circle lines in NCERT ch.3.
    """
    low_fn = (filename or "").lower()
    if re.search(r"trigonometric|trigonometry", low_fn):
        return "trigonometry", "filename_hint", 0.9

    focus = (topic_focus or "").strip()
    if focus:
        fscores = score_chapters_from_text(focus)
        if fscores:
            best = max(fscores, key=fscores.get)
            total = sum(fscores.values()) or 1
            return best, "topic_focus", min(0.98, 0.55 + fscores[best] / total * 0.4)

    content = score_chapters_from_text(blob)
    fn_hint = score_chapters_from_filename(filename)
    fn_weight = 1.0 if _filename_names_chapter_explicitly(filename) else 0.35

    merged: Dict[str, float] = {}
    for ch, sc in content.items():
        merged[ch] = merged.get(ch, 0) + sc
    for ch, sc in fn_hint.items():
        merged[ch] = merged.get(ch, 0) + sc * fn_weight

    # Exercise lines only — not full PDF (NCERT ch.3 mixes one circle drill with trig)
    sub_text = "\n".join(subtopics or [])
    sub_dom = dominant_chapter_from_text(sub_text) if sub_text else None
    if sub_dom:
        sub_ch, sub_sc = sub_dom
        merged[sub_ch] = merged.get(sub_ch, 0) + sub_sc * 1.2

    if not merged:
        return "generic", "pdf_content", 0.0

    best = max(merged, key=merged.get)
    total = sum(merged.values()) or 1
    conf = merged[best] / total
    source = "pdf_content"

    if fn_hint.get(best, 0) > 0 and fn_weight >= 1.0:
        source = "filename_hint"
    elif sub_dom and sub_dom[0] == best:
        source = "pdf_subtopics"
    return best, source, round(min(0.95, 0.35 + conf * 0.55), 3)


def extract_primary_topic_from_pdf(
    *,
    blob: str,
    filename: str = "",
    topic_focus: str = "",
) -> str:
    if topic_focus.strip():
        return topic_focus.strip()[:80]
    for pat in (_CHAPTER_TITLE,):
        m = pat.search(blob or "")
        if m:
            title = re.sub(r"\s+", " ", m.group(1).strip())
            if len(title) > 4 and not re.fullmatch(r"[\divxlcdm\d\s]+", title, re.I):
                return title[:80]
    stem = re.sub(r"[_\.\-]+", " ", (filename or "").rsplit(".", 1)[0])
    stem = re.sub(
        r"\b(class|maths|mathematics|ncert|chapter)\b",
        " ",
        stem,
        flags=re.I,
    )
    stem = re.sub(r"\s+", " ", stem).strip()
    if len(stem) > 6:
        return stem.title()[:80]
    return ""


def extract_subtopics_from_pdf(blob: str, *, limit: int = 20) -> List[str]:
    """Exercises, examples, theorem lines, and numbered items from PDF text."""
    out: List[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        label = re.sub(r"\s+", " ", (label or "").strip())[:90]
        key = label.lower()
        if len(label) < 6 or key in seen:
            return
        seen.add(key)
        out.append(label)

    for m in _EXERCISE_LINE.finditer(blob or ""):
        add(f"Exercise {m.group(1)}")
    for m in _EXERCISE_ITEM.finditer(blob or ""):
        add(f"{m.group(1)}. {m.group(2).strip()}")
    for m in _THEOREM_HEADING.finditer(blob or ""):
        num, body = m.group(1) or "", m.group(2).strip()
        add(f"Theorem {num}: {body}" if num else body)
    for m in _THEOREM_NAMED.finditer(blob or ""):
        add(m.group(1).strip().title())
    for m in _FORMULA_IDENTITY.finditer(blob or ""):
        add(f"Identity: {m.group(1).strip()}")
    return out[:limit]


def _infer_archetype_from_label(label: str) -> str:
    low = (label or "").lower()
    if re.search(r"\bprove\b|\bshow\s+that\b", low):
        return "proof_derive"
    if re.search(r"\bidentity\b", low):
        return "identity_prove"
    if re.search(r"\bradian\b|\bdegree\b", low):
        return "radian_degree"
    if re.search(r"\btangent\b|\bsecant\b|\bchord\b", low):
        return "length_find"
    if re.search(r"\barea\b|\bfind\b|\bcalculate\b", low):
        return "numerical_find"
    return "concept_apply"


def extract_theorems_from_pdf(
    blob: str,
    subtopics: Optional[List[str]] = None,
    *,
    max_theorems: int = 8,
) -> List[Dict[str, Any]]:
    """
    Theorems / results stated in the PDF — not a static chapter catalog dump.
    """
    text = (blob or "") + "\n" + "\n".join(subtopics or [])
    found: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    def push(label: str, *, importance: str = "important") -> None:
        label = re.sub(r"\s+", " ", label.strip())[:140]
        if len(label) < 8:
            return
        tid = _slug_id(label)
        if tid in seen_ids:
            return
        seen_ids.add(tid)
        found.append(
            {
                "id": tid,
                "label": label,
                "archetype_id": _infer_archetype_from_label(label),
                "importance": importance,
                "source": "pdf_extract",
            }
        )

    for m in _THEOREM_HEADING.finditer(text):
        num, body = m.group(1) or "", m.group(2).strip()
        label = f"Theorem {num}: {body}" if num else body
        push(label, importance="required")
    for m in _THEOREM_NAMED.finditer(text):
        push(m.group(1).strip().title(), importance="required")
    for m in _PROVE_BLOCK.finditer(text):
        push(f"Prove that {m.group(1).strip()}", importance="important")
    for m in _FORMULA_IDENTITY.finditer(text):
        push(f"Identity: {m.group(1).strip()}", importance="important")

    # Exercise stems that reference standard results (PDF-only labels)
    for line in (subtopics or []):
        if re.search(r"\btheorem\b|\bprove\b|\bidentity\b", line, re.I):
            push(line, importance="important")

    return found[:max_theorems]


def extract_skill_concepts_from_pdf(
    blob: str,
    chapter: str,
    *,
    max_items: int = 6,
) -> List[Dict[str, Any]]:
    """
    When no formal 'Theorem N' lines exist, build plan items from repeated PDF skills.
    """
    from app.generation.theorem_coverage import catalog_for_chapter

    pdf_thms = extract_theorems_from_pdf(blob, max_theorems=max_items)
    if pdf_thms:
        return pdf_thms

    text = blob or ""
    low = text.lower()
    dynamic: List[Dict[str, Any]] = []
    seen: set[str] = set()

    skill_patterns = (
        (r"\bradian\s+measure|\bdegree\s+measure", "Radian and degree measure"),
        (r"\bsin\s*[\(\sx]|\bcos\s*[\(\sx]|\btan\s*[\(\sx]", "Trigonometric ratios"),
        (r"\bprove\s+that.*\b(?:sin|cos|tan|sec|cosec)", "Trigonometric identities"),
        (r"\btangent.*radius|perpendicular.*tangent", "Tangent perpendicular to radius"),
        (r"\btangents?\s+from\s+an?\s+external\s+point", "Equal tangents from external point"),
        (r"\bsecant|tangent.*power", "Secant–tangent relation"),
        (r"\bdiscriminant|nature\s+of\s+roots", "Nature of roots"),
        (r"\bsimilar\s+triangles", "Similar triangles"),
        (r"\bcongruence|\bRHS|\bSAS", "Triangle congruence"),
        (r"\bpythagoras", "Pythagoras theorem"),
        (r"\bparallelogram|\brhombus|\btrapezium", "Quadrilateral properties"),
        (r"\barithmetic\s+progression|\bcommon\s+difference", "Arithmetic progression"),
    )
    for pat, label in skill_patterns:
        if re.search(pat, low, re.I):
            tid = _slug_id(label)
            if tid not in seen:
                seen.add(tid)
                dynamic.append(
                    {
                        "id": tid,
                        "label": label,
                        "archetype_id": _infer_archetype_from_label(label),
                        "importance": "important",
                        "source": "pdf_skill",
                    }
                )

    if dynamic:
        return dynamic[:max_items]

    # Only if PDF has almost no signals: minimal catalog fallback
    if len(text.strip()) < 200:
        return [
            {**t, "source": "catalog_fallback"}
            for t in catalog_for_chapter(chapter)[:max_items]
        ]
    return []
