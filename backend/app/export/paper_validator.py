"""
Automated paper validation — math feasibility, LaTeX leaks, content completeness.
Used before PDF export (rejects below threshold).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.generation.answer_sync import answer_stem_value_mismatches
from app.generation.question_text import has_raw_latex

_TOLERANCE = 0.001
_RAW_LATEX_EXTRA = re.compile(
    r"\\mathsf\{|\\mathbf\{|\\wedge|\\times|\\frac\{|\\sqrt\{",
    re.I,
)
_GLUE_BUGS = re.compile(
    r"2touching|cmant|\bfro\s+GH\b|\bfro\s+[A-Z]{2}\b|5\.0mar|6\.0mar",
    re.I,
)
_FUSION_MARK = re.compile(
    r"configuration\s+of\s+question\s+1|using\s+the\s+configuration\s+in\s+question\s+1",
    re.I,
)
_Q5_OG_PHRASE = re.compile(r"\bfrom\s+O\b", re.I)
_Q5_FUSION_TANGENT = re.compile(r"\btangent\s+[A-Z]{2}\b", re.I)
_TRUNCATED_FROM = re.compile(r"\bfro\s+(?!m\b)", re.I)
_PLAIN_EXPONENT = re.compile(r"\b([A-Z]{2})2(?==|\s*×)", re.I)
_QUESTION_GLUE = re.compile(r"Question\s+\d+[a-zA-Z]", re.I)
_ANSWER_GARBAGE = re.compile(
    r"the\s+fu\s+secant|full\s+secant\s+P\s+to\s+T|modelssq|mathsf\s+mathsf",
    re.I,
)
_PLAIN_SQRT_PHRASE = re.compile(r"\bsquare\s+root\s+of\b", re.I)
_MATHSF_LEAK = re.compile(r"\bmathsf\b", re.I)
_WRONG_PB_SECANT = re.compile(r"\bPB\s*=\s*\d", re.I)
_TRUNCATED_NOTE = re.compile(r"Note:\s*[A-Z]\s+anchor|R2-r2is|perf\s*$", re.I)


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str
    message: str


@dataclass
class PaperValidationReport:
    paper_id: str = ""
    results: List[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(
            not r.passed and r.severity in ("CRITICAL", "HIGH") for r in self.results
        )

    @property
    def errors(self) -> List[str]:
        return [r.message for r in self.results if not r.passed]

    def add(self, name: str, passed: bool, severity: str, message: str) -> None:
        self.results.append(CheckResult(name, passed, severity, message))


def _parse_radii_concentric(text: str) -> Optional[Tuple[float, float]]:
    m = re.search(
        r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    )
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    return (max(a, b), min(a, b))


def _check_concentric(R: float, r: float) -> Tuple[bool, str]:
    if r >= R:
        return False, f"inner r={r} >= outer R={R}"
    half = math.sqrt(R * R - r * r)
    chord = 2 * half
    clean = half == int(half)
    return True, f"DE={chord:.4g}" + (" (integer)" if clean else "")


def _check_external_tangent(r1: float, r2: float, d: float) -> Tuple[bool, str]:
    diff = abs(r2 - r1)
    if d <= diff:
        return False, f"d={d} <= |r2-r1|={diff} (no external tangent)"
    if d <= r1 + r2:
        return False, f"d={d} <= r1+r2={r1+r2} (circles intersect)"
    length = math.sqrt(d * d - diff * diff)
    return True, f"EF={length:.4g}"


def validate_questions_for_pdf(
    questions: List[Dict[str, Any]],
    *,
    paper_id: str = "",
) -> Dict[str, Any]:
    """Validate question dicts before ReportLab build. Returns {ok, errors, warnings}."""
    report = PaperValidationReport(paper_id=paper_id or "paper")
    outer_r: Optional[float] = None

    for i, q in enumerate(questions):
        slot = int(q.get("slot_number") or i + 1)
        content = (q.get("content") or q.get("question") or "").strip()
        if not content:
            report.add(f"q{slot}_content", False, "CRITICAL", f"Q{slot}: empty stem")
            continue

        if has_raw_latex(content) or _RAW_LATEX_EXTRA.search(content):
            report.add(
                f"q{slot}_latex",
                False,
                "CRITICAL",
                f"Q{slot}: raw LaTeX in stem",
            )

        if _GLUE_BUGS.search(content) or _TRUNCATED_FROM.search(content):
            report.add(
                f"q{slot}_glue",
                False,
                "HIGH",
                f"Q{slot}: truncated/glue text (e.g. fro GH, 2touching)",
            )

        stem_text = (q.get("content") or q.get("question") or "").strip()
        ans_text = (q.get("correct_answer") or "").strip()
        if stem_text and ans_text:
            mism = answer_stem_value_mismatches(stem_text, ans_text)
            if mism:
                report.add(
                    f"q{slot}_answer_mismatch",
                    False,
                    "CRITICAL",
                    f"Q{slot}: answer key values ≠ question — {', '.join(mism[:4])}",
                )

        for key in ("content", "correct_answer", "explanation"):
            val = (q.get(key) or q.get("question") if key == "content" else q.get(key)) or ""
            if not isinstance(val, str):
                continue
            if key == "correct_answer":
                if _ANSWER_GARBAGE.search(val):
                    report.add(
                        f"q{slot}_answer_garbage",
                        False,
                        "HIGH",
                        f"Q{slot}: answer key garbage text (secant PT / mathsf / modelssq)",
                    )
                if _PLAIN_SQRT_PHRASE.search(val):
                    report.add(
                        f"q{slot}_answer_sqrt",
                        False,
                        "HIGH",
                        f"Q{slot}: use √ not 'square root of' in answer",
                    )
                if _MATHSF_LEAK.search(val):
                    report.add(
                        f"q{slot}_answer_mathsf",
                        False,
                        "HIGH",
                        f"Q{slot}: raw mathsf remnant in answer",
                    )
                if _WRONG_PB_SECANT.search(val) and re.search(
                    r"\bFind\s+PR\b|\bPR\b", stem_text, re.I
                ):
                    report.add(
                        f"q{slot}_answer_pb",
                        False,
                        "CRITICAL",
                        f"Q{slot}: answer uses PB but question asks for PR",
                    )
            if key == "explanation" and val and _TRUNCATED_NOTE.search(val):
                report.add(
                    f"q{slot}_note_trunc",
                    False,
                    "MEDIUM",
                    f"Q{slot}: truncated or corrupted Note text",
                )
            if key in ("content", "question") and _MATHSF_LEAK.search(val):
                report.add(
                    f"q{slot}_stem_mathsf",
                    False,
                    "HIGH",
                    f"Q{slot}: raw mathsf in question stem",
                )
            if _PLAIN_EXPONENT.search(val):
                report.add(
                    f"q{slot}_{key}_exp",
                    False,
                    "HIGH",
                    f"Q{slot} {key}: use ² not 2 (e.g. PA²= not PA2=)",
                )
            if _QUESTION_GLUE.search(val) or "2touching" in val.lower():
                report.add(
                    f"q{slot}_{key}_qglue",
                    False,
                    "HIGH",
                    f"Q{slot} {key}: missing space after Question N",
                )

        if slot == 5 or (slot == len(questions) and _FUSION_MARK.search(content)):
            if _FUSION_MARK.search(content):
                if not _Q5_OG_PHRASE.search(content):
                    report.add(
                        f"q{slot}_fusion_from_o",
                        False,
                        "CRITICAL",
                        f"Q{slot}: fusion stem missing 'from O' (data loss?)",
                    )
                if not _Q5_FUSION_TANGENT.search(content):
                    report.add(
                        f"q{slot}_fusion_tangent",
                        False,
                        "CRITICAL",
                        f"Q{slot}: fusion stem missing tangent segment (e.g. tangent GH or tangent LM)",
                    )

        if slot == 1:
            radii = _parse_radii_concentric(content)
            if radii:
                outer_r = radii[0]
                ok, msg = _check_concentric(radii[0], radii[1])
                report.add(f"q1_math", ok, "CRITICAL" if not ok else "LOW", f"Q1: {msg}")

        if slot == 4:
            m = re.search(
                r"radii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm.*?GH\s*=\s*(\d+(?:\.\d+)?)\s*cm",
                content,
                re.I | re.S,
            )
            if m:
                ok, msg = _check_external_tangent(
                    float(m.group(1)), float(m.group(2)), float(m.group(3))
                )
                report.add(f"q4_math", ok, "CRITICAL" if not ok else "LOW", f"Q4: {msg}")

        if q.get("question_type") == "FigureBased" and not q.get("figure_url"):
            report.add(
                f"q{slot}_fig",
                False,
                "HIGH",
                f"Q{slot}: FigureBased without figure_url",
            )

    # Duplicate stems (simple)
    stems = [(q.get("slot_number") or i + 1, (q.get("content") or "")[:200]) for i, q in enumerate(questions)]
    for i, (s1, t1) in enumerate(stems):
        for s2, t2 in stems[i + 1 :]:
            w1 = set(t1.lower().split())
            w2 = set(t2.lower().split())
            if w1 and w2:
                sim = len(w1 & w2) / len(w1 | w2)
                if sim > 0.72:
                    report.add(
                        "duplicate",
                        False,
                        "CRITICAL",
                        f"Q{s1} and Q{s2} stems {sim:.0%} similar",
                    )

    errors = [r.message for r in report.results if not r.passed and r.severity in ("CRITICAL", "HIGH")]
    warnings = [r.message for r in report.results if not r.passed and r.severity not in ("CRITICAL", "HIGH")]
    return {
        "ok": report.ok,
        "errors": errors,
        "warnings": warnings,
        "results": report.results,
    }


def validate_pdf_text(extracted_text: str, *, paper_id: str = "") -> Dict[str, Any]:
    """Validate extracted PDF text (PyPDF2-style — same as validate_assessment_pdf.py)."""
    report = PaperValidationReport(paper_id=paper_id)
    if has_raw_latex(extracted_text) or _RAW_LATEX_EXTRA.search(extracted_text):
        report.add("pdf_latex", False, "CRITICAL", "PDF text layer contains raw LaTeX")
    if _GLUE_BUGS.search(extracted_text) or _TRUNCATED_FROM.search(extracted_text):
        report.add("pdf_glue", False, "HIGH", "PDF text: fro GH / glue fragments")
    corrupted_figs = re.findall(
        r"F\s+i\s+g\.?\s*\d+",
        extracted_text,
        re.I,
    )
    clean_figs = re.findall(r"Fig\.\d+", extracted_text, re.I)
    if corrupted_figs:
        report.add(
            "pdf_fig_label",
            False,
            "MEDIUM",
            f"PDF extract: spaced fig labels {corrupted_figs[:3]} (clean: {len(clean_figs)})",
        )
    if "2touching" in extracted_text.lower() or _QUESTION_GLUE.search(extracted_text):
        report.add("pdf_2touching", False, "HIGH", "PDF text: Question 2touching / glued")
    for m in _PLAIN_EXPONENT.finditer(extracted_text):
        report.add(
            "pdf_exponent",
            False,
            "MEDIUM",
            f"PDF text: {m.group(0)} should use ² (e.g. {m.group(1)}²=)",
        )
        break
    errors = [r.message for r in report.results if not r.passed]
    return {"ok": not errors, "errors": errors}
