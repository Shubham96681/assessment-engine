"""
CBSE question-paper benchmark — dynamic quality floors from local PDF corpus.

Scans CBSE_QuestionPapers/ (when PDFs exist), profiles stem metrics with the same
scorers used at generation time, and sets reject/accept floors from percentiles
(not fixed constants like 0.38).
"""
from __future__ import annotations

import json
import logging
import re
import statistics
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.generation.cbse_question_extract import (
    class_to_band,
    extract_stems_from_pdf_text,
)

logger = logging.getLogger(__name__)

_CACHE: Optional[Dict[str, Any]] = None
_CACHE_MTIME: float = 0.0


@dataclass
class BandProfile:
    sample_count: int = 0
    word_count_p25: float = 12.0
    word_count_p50: float = 22.0
    word_count_p75: float = 38.0
    word_count_p90: float = 52.0
    authenticity_p25: float = 0.45
    authenticity_p50: float = 0.58
    authenticity_p75: float = 0.68
    authenticity_p90: float = 0.78
    combined_p25: float = 0.38
    combined_p50: float = 0.48
    combined_p75: float = 0.55
    combined_p90: float = 0.62
    exam_verb_rate: float = 0.85
    subpart_rate: float = 0.35
    marks_median: float = 3.0
    # Floors for generated questions (above CBSE p75)
    min_combined_floor: float = 0.42
    min_authenticity_floor: float = 0.52
    min_word_count_soft: float = 14.0
    target_word_count: float = 24.0


@dataclass
class BenchmarkSnapshot:
    built_at: float = 0.0
    pdf_count: int = 0
    stem_count: int = 0
    bands: Dict[str, BandProfile] = field(default_factory=dict)
    source_root: str = ""

    def band_for_class(self, class_level: str) -> BandProfile:
        band = _class_level_to_band(class_level)
        if band in self.bands and self.bands[band].sample_count >= 5:
            return self.bands[band]
        if "all" in self.bands and self.bands["all"].sample_count >= 5:
            return self.bands["all"]
        return _profile_from_rule_packs(band)


def _class_level_to_band(class_level: str) -> str:
    m = re.search(r"\d{1,2}", str(class_level or ""))
    if not m:
        return "all"
    return class_to_band(m.group(0))


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    vals = sorted(vals)
    idx = min(len(vals) - 1, max(0, int(len(vals) * p)))
    return float(vals[idx])


def _resolve_cbse_root() -> Path:
    root = Path(settings.CBSE_BENCHMARK_ROOT)
    if not root.is_absolute():
        # project root = parent of backend/
        backend = Path(__file__).resolve().parents[2]
        root = (backend.parent / root).resolve()
    return root


def _cache_path() -> Path:
    p = Path(settings.CBSE_BENCHMARK_CACHE_PATH)
    if not p.is_absolute():
        backend = Path(__file__).resolve().parents[2]
        p = (backend / p).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _score_stem_like_generation(stem: Dict[str, Any]) -> Dict[str, float]:
    """Run the same lightweight metrics used for generated questions."""
    from app.generation.authenticity import TextbookAuthenticityScorer
    from app.generation.quality import QualityScorer

    q = {
        "content": stem.get("content") or "",
        "question_type": "ShortAnswer",
        "marks": stem.get("marks") or 3,
        "order_index": 0,
    }
    scorer = QualityScorer()
    auth = TextbookAuthenticityScorer()
    auth.score_question(q, slot_band="L3")
    scorer._apply_completeness_and_combined(q, "L3", ui_difficulty="medium")
    return {
        "authenticity": float(q.get("authenticity_score") or 0),
        "combined": float(q.get("combined_score") or 0),
        "quality": float(q.get("quality_score") or 0),
        "word_count": float(stem.get("word_count") or len((q.get("content") or "").split())),
    }


def _profile_from_rule_packs(band: str) -> BandProfile:
    """When no CBSE PDFs on disk — derive targets from chapter rule-pack exemplars."""
    from app.generation.chapter_rule_packs import CHAPTER_RULES
    from app.generation.authenticity import TextbookAuthenticityScorer

    auth = TextbookAuthenticityScorer()
    words: List[float] = []
    auths: List[float] = []
    for pack in CHAPTER_RULES.values():
        for ex in (pack.embedding_anchors or ())[:4]:
            if not ex or len(ex.split()) < 8:
                continue
            q = {"content": ex, "question_type": "ShortAnswer", "marks": 3}
            auth.score_question(q, slot_band="L3")
            words.append(len(ex.split()))
            auths.append(float(q.get("authenticity_score") or 0.5))
        if pack.stem_example and len(pack.stem_example.split()) >= 8:
            q = {"content": pack.stem_example, "question_type": "ShortAnswer", "marks": 3}
            auth.score_question(q, slot_band="L3")
            words.append(len(pack.stem_example.split()))
            auths.append(float(q.get("authenticity_score") or 0.5))

    if not words:
        words = [18.0, 24.0, 32.0]
        auths = [0.55, 0.62, 0.70]

    p50_w = statistics.median(words)
    p75_w = _percentile(words, 0.75)
    p50_a = statistics.median(auths)
    p75_a = _percentile(auths, 0.75)
    spread = max(0.04, p75_a - p50_a)
    return BandProfile(
        sample_count=len(words),
        word_count_p50=p50_w,
        word_count_p75=p75_w,
        word_count_p90=_percentile(words, 0.9),
        authenticity_p50=p50_a,
        authenticity_p75=p75_a,
        authenticity_p90=_percentile(auths, 0.9),
        combined_p50=p50_a * 0.85,
        combined_p75=p75_a * 0.85 + spread,
        combined_p90=p75_a * 0.85 + spread * 1.5,
        min_combined_floor=min(0.95, p75_a * 0.85 + spread * 0.5),
        min_authenticity_floor=min(0.95, p75_a + spread * 0.35),
        min_word_count_soft=max(10.0, p50_w * 0.85),
        target_word_count=p75_w,
    )


def _aggregate_band(rows: List[Dict[str, Any]]) -> BandProfile:
    if not rows:
        return BandProfile()

    wc = [r["word_count"] for r in rows]
    au = [r["authenticity"] for r in rows]
    co = [r["combined"] for r in rows]
    verbs = [1.0 if r.get("exam_verb_count", 0) > 0 else 0.0 for r in rows]
    subs = [1.0 if r.get("subpart_count", 0) > 0 else 0.0 for r in rows]
    marks = [r["marks"] for r in rows if r.get("marks")]

    p25_a = _percentile(au, 0.25)
    p50_a = _percentile(au, 0.5)
    p75_a = _percentile(au, 0.75)
    p25_c = _percentile(co, 0.25)
    p50_c = _percentile(co, 0.5)
    p75_c = _percentile(co, 0.75)

    # Floors: above typical board median (p50), not raw p75 (our scorer inflates CBSE stems).
    # Reject only below board p25; target p75+ for "above paper level".
    min_combined = max(0.48, p25_c + (p50_c - p25_c) * 0.55)
    min_auth = max(0.52, p25_a + (p50_a - p25_a) * 0.5)

    return BandProfile(
        sample_count=len(rows),
        word_count_p25=_percentile(wc, 0.25),
        word_count_p50=_percentile(wc, 0.5),
        word_count_p75=_percentile(wc, 0.75),
        word_count_p90=_percentile(wc, 0.9),
        authenticity_p25=p25_a,
        authenticity_p50=p50_a,
        authenticity_p75=p75_a,
        authenticity_p90=_percentile(au, 0.9),
        combined_p25=p25_c,
        combined_p50=p50_c,
        combined_p75=p75_c,
        combined_p90=_percentile(co, 0.9),
        exam_verb_rate=sum(verbs) / len(verbs),
        subpart_rate=sum(subs) / len(subs),
        marks_median=statistics.median(marks) if marks else 3.0,
        min_combined_floor=min(0.88, min_combined),
        min_authenticity_floor=min(0.88, min_auth),
        min_word_count_soft=max(8.0, _percentile(wc, 0.25) * 0.85),
        target_word_count=_percentile(wc, 0.75),
    )


def build_benchmark(*, force: bool = False) -> BenchmarkSnapshot:
    """Scan CBSE PDF folder and write benchmark cache."""
    global _CACHE, _CACHE_MTIME
    root = _resolve_cbse_root()
    pdfs = list(root.rglob("*.pdf")) + list(root.rglob("*.PDF"))
    by_band: Dict[str, List[Dict[str, Any]]] = {
        "middle": [],
        "secondary": [],
        "senior": [],
        "all": [],
    }

    for pdf in pdfs:
        try:
            import fitz

            doc = fitz.open(str(pdf))
            text = "\n".join(page.get_text("text") for page in doc)
            doc.close()
        except Exception as exc:
            logger.warning("CBSE benchmark skip %s: %s", pdf.name, exc)
            continue
        rel = str(pdf.relative_to(root)) if pdf.is_relative_to(root) else pdf.name
        for stem in extract_stems_from_pdf_text(text, source_file=rel):
            scored = _score_stem_like_generation(stem)
            row = {**stem, **scored}
            band = stem.get("class_band") or "all"
            by_band.setdefault(band, []).append(row)
            by_band["all"].append(row)

    snap = BenchmarkSnapshot(
        built_at=time.time(),
        pdf_count=len(pdfs),
        stem_count=len(by_band.get("all", [])),
        source_root=str(root),
    )
    for band, rows in by_band.items():
        snap.bands[band] = _aggregate_band(rows) if rows else _profile_from_rule_packs(band)

    if snap.stem_count < 5:
        logger.info(
            "CBSE benchmark: no/few PDFs in %s — using rule-pack derived floors",
            root,
        )
        for b in ("middle", "secondary", "senior", "all"):
            if b not in snap.bands or snap.bands[b].sample_count < 5:
                snap.bands[b] = _profile_from_rule_packs(b)

    cache = {
        "built_at": snap.built_at,
        "pdf_count": snap.pdf_count,
        "stem_count": snap.stem_count,
        "source_root": snap.source_root,
        "bands": {k: asdict(v) for k, v in snap.bands.items()},
    }
    _cache_path().write_text(json.dumps(cache, indent=2), encoding="utf-8")
    _CACHE = cache
    _CACHE_MTIME = _cache_path().stat().st_mtime
    logger.info(
        "CBSE benchmark built: %d PDFs, %d stems, floors from percentiles",
        snap.pdf_count,
        snap.stem_count,
    )
    return snap


def load_benchmark(*, rebuild_if_stale: bool = True) -> BenchmarkSnapshot:
    global _CACHE, _CACHE_MTIME
    cache_file = _cache_path()
    root = _resolve_cbse_root()
    pdfs = list(root.rglob("*.pdf")) + list(root.rglob("*.PDF"))

    def _from_dict(data: Dict[str, Any]) -> BenchmarkSnapshot:
        snap = BenchmarkSnapshot(
            built_at=data.get("built_at", 0),
            pdf_count=data.get("pdf_count", 0),
            stem_count=data.get("stem_count", 0),
            source_root=data.get("source_root", ""),
        )
        for k, v in (data.get("bands") or {}).items():
            snap.bands[k] = BandProfile(**v)
        return snap

    newest_pdf = max((p.stat().st_mtime for p in pdfs), default=0)
    stale = (
        not cache_file.exists()
        or (newest_pdf and cache_file.stat().st_mtime < newest_pdf)
        or (time.time() - cache_file.stat().st_mtime) > settings.CBSE_BENCHMARK_MAX_AGE_HOURS * 3600
    )

    if rebuild_if_stale and stale and settings.ENABLE_CBSE_BENCHMARK:
        return build_benchmark()

    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            _CACHE = data
            _CACHE_MTIME = cache_file.stat().st_mtime
            return _from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("CBSE benchmark cache read failed: %s", exc)

    if settings.ENABLE_CBSE_BENCHMARK and pdfs:
        return build_benchmark()

    snap = BenchmarkSnapshot(source_root=str(root))
    for b in ("middle", "secondary", "senior", "all"):
        snap.bands[b] = _profile_from_rule_packs(b)
    return snap


def evaluate_against_cbse(
    q: Dict[str, Any],
    *,
    class_level: str = "10",
    slot_band: str = "L3",
) -> Dict[str, Any]:
    """
    Compare one generated question to CBSE benchmark profile.
    Returns scores, flags, and dynamic floor used.
    """
    if not settings.ENABLE_CBSE_BENCHMARK:
        return {"cbse_gate_enabled": False}

    snap = load_benchmark()
    prof = snap.band_for_class(class_level)
    content = (q.get("content") or "").strip()
    n_words = len(content.split())
    low = content.lower()

    flags: List[str] = []
    score = 0.72

    if n_words < prof.min_word_count_soft:
        flags.append("below_cbse_stem_length_p25")
        score -= 0.12
    elif n_words >= prof.target_word_count:
        score += 0.08

    auth = float(q.get("authenticity_score") or 0)
    comb = float(q.get("combined_score") or 0)

    if auth < prof.min_authenticity_floor:
        flags.append("below_cbse_authenticity_floor")
        score -= 0.15
    elif auth >= prof.authenticity_p75:
        score += 0.06

    if comb < prof.combined_p25:
        flags.append("below_cbse_combined_p25")
        score -= 0.22
    elif comb < prof.min_combined_floor:
        flags.append("below_cbse_combined_floor")
        score -= 0.12
    elif comb >= prof.combined_p75:
        score += 0.08
    elif comb >= prof.combined_p90:
        score += 0.05

    if prof.exam_verb_rate > 0.7 and not re.search(
        r"\bfind\b|\bprove\b|\bshow\b|\bcalculate\b|\bevaluate\b|\bsolve\b|\bif\b",
        low,
    ):
        flags.append("missing_exam_command_verb")
        score -= 0.1

    cbse_alignment = max(0.0, min(1.0, score))
    above_cbse = (
        comb >= prof.combined_p75
        and auth >= prof.authenticity_p75
        and n_words >= prof.min_word_count_soft
        and "missing_exam_command_verb" not in flags
        and "below_cbse_combined_p25" not in flags
    )

    return {
        "cbse_gate_enabled": True,
        "cbse_alignment_score": round(cbse_alignment, 3),
        "cbse_above_paper_level": above_cbse,
        "cbse_flags": flags,
        "cbse_min_combined_floor": prof.min_combined_floor,
        "cbse_min_authenticity_floor": prof.min_authenticity_floor,
        "cbse_target_words": prof.target_word_count,
        "cbse_sample_count": prof.sample_count,
        "cbse_reject": bool(flags) and not above_cbse,
    }


def apply_cbse_benchmark_to_questions(
    questions: List[Dict[str, Any]],
    *,
    class_level: str = "10",
) -> List[Dict[str, Any]]:
    if not settings.ENABLE_CBSE_BENCHMARK:
        return questions
    for q in questions:
        rep = evaluate_against_cbse(q, class_level=class_level)
        q.update(rep)
        if rep.get("cbse_above_paper_level"):
            uplift = min(0.08, (rep["cbse_alignment_score"] - 0.65) * 0.12)
            q["combined_score"] = round(
                min(1.0, float(q.get("combined_score", 0)) + uplift), 3
            )
        elif rep.get("cbse_reject"):
            q["combined_score"] = round(
                max(0.0, float(q.get("combined_score", 0)) - 0.12), 3
            )
    return questions


def get_dynamic_combined_floor(class_level: str = "10") -> float:
    if not settings.ENABLE_CBSE_BENCHMARK:
        return 0.38
    snap = load_benchmark()
    return snap.band_for_class(class_level).min_combined_floor


def benchmark_prompt_hints(class_level: str = "10") -> str:
    """Inject into compiler — targets derived from CBSE corpus or rule packs."""
    if not settings.ENABLE_CBSE_BENCHMARK:
        return ""
    prof = load_benchmark().band_for_class(class_level)
    if prof.sample_count < 1:
        return ""
    return (
        f"QUALITY BAR (from {prof.sample_count} board-paper stems): "
        f"stems ~{int(prof.target_word_count)} words; "
        f"exam verbs (find/prove/calculate); "
        f"authenticity above {prof.min_authenticity_floor:.2f}; "
        f"no meta language; match CBSE SQP compression."
    )
