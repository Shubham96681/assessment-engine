"""
GATE exam benchmark — dynamic quality floors from GATE_QuestionPapers/*.pdf
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.generation.cbse_benchmark import (
    BandProfile,
    BenchmarkSnapshot,
    _aggregate_band,
    _cache_path as _cbse_cache_path_unused,
    _percentile,
    _profile_from_rule_packs,
    _score_stem_like_generation,
)
from app.generation.gate_question_extract import (
    extract_stems_from_gate_pdf_text,
    should_index_pdf,
)

logger = logging.getLogger(__name__)

_CACHE: Optional[Dict[str, Any]] = None


def _resolve_gate_root() -> Path:
    root = Path(settings.GATE_BENCHMARK_ROOT)
    if not root.is_absolute():
        backend = Path(__file__).resolve().parents[2]
        root = (backend.parent / root).resolve()
    return root


def _cache_path() -> Path:
    p = Path(settings.GATE_BENCHMARK_CACHE_PATH)
    if not p.is_absolute():
        backend = Path(__file__).resolve().parents[2]
        p = (backend / p).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _boost_gate_profile(prof: BandProfile) -> BandProfile:
    """GATE stems are longer and deeper than board papers — raise floors modestly."""
    return BandProfile(
        sample_count=prof.sample_count,
        word_count_p25=prof.word_count_p25 * 1.1,
        word_count_p50=prof.word_count_p50 * 1.15,
        word_count_p75=prof.word_count_p75 * 1.12,
        word_count_p90=prof.word_count_p90 * 1.1,
        authenticity_p25=prof.authenticity_p25,
        authenticity_p50=prof.authenticity_p50,
        authenticity_p75=min(0.95, prof.authenticity_p75 + 0.04),
        authenticity_p90=min(0.95, prof.authenticity_p90 + 0.03),
        combined_p25=min(0.95, prof.combined_p25 + 0.05),
        combined_p50=min(0.95, prof.combined_p50 + 0.06),
        combined_p75=min(0.95, prof.combined_p75 + 0.07),
        combined_p90=min(0.95, prof.combined_p90 + 0.05),
        exam_verb_rate=prof.exam_verb_rate,
        subpart_rate=max(prof.subpart_rate, 0.45),
        marks_median=max(prof.marks_median, 2.0),
        min_combined_floor=min(0.92, prof.min_combined_floor + 0.06),
        min_authenticity_floor=min(0.92, prof.min_authenticity_floor + 0.05),
        min_word_count_soft=max(18.0, prof.min_word_count_soft * 1.2),
        target_word_count=max(32.0, prof.target_word_count * 1.15),
    )


def build_gate_benchmark(*, force: bool = False) -> BenchmarkSnapshot:
    global _CACHE
    root = _resolve_gate_root()
    pdfs = [
        p
        for p in sorted(set(root.rglob("*.pdf")) | set(root.rglob("*.PDF")))
        if should_index_pdf(str(p.relative_to(root) if p.is_relative_to(root) else p.name))
    ]
    rows: List[Dict[str, Any]] = []
    for pdf in pdfs:
        try:
            import fitz

            doc = fitz.open(str(pdf))
            text = "\n".join(page.get_text("text") for page in doc)
            doc.close()
        except Exception as exc:
            logger.warning("GATE benchmark skip %s: %s", pdf.name, exc)
            continue
        rel = str(pdf.relative_to(root)) if pdf.is_relative_to(root) else pdf.name
        for stem in extract_stems_from_gate_pdf_text(text, source_file=rel):
            rows.append({**stem, **_score_stem_like_generation(stem)})

    snap = BenchmarkSnapshot(
        built_at=time.time(),
        pdf_count=len(pdfs),
        stem_count=len(rows),
        source_root=str(root),
    )
    if rows:
        snap.bands["gate"] = _boost_gate_profile(_aggregate_band(rows))
        snap.bands["all"] = snap.bands["gate"]
    else:
        logger.info("GATE benchmark: no PDFs in %s — using boosted rule-pack floors", root)
        snap.bands["gate"] = _boost_gate_profile(_profile_from_rule_packs("senior"))
        snap.bands["all"] = snap.bands["gate"]

    cache = {
        "built_at": snap.built_at,
        "pdf_count": snap.pdf_count,
        "stem_count": snap.stem_count,
        "source_root": snap.source_root,
        "bands": {k: asdict(v) for k, v in snap.bands.items()},
    }
    _cache_path().write_text(json.dumps(cache, indent=2), encoding="utf-8")
    _CACHE = cache
    logger.info(
        "GATE benchmark built: %d PDFs, %d stems",
        snap.pdf_count,
        snap.stem_count,
    )
    return snap


def load_gate_benchmark(*, rebuild_if_stale: bool = True) -> BenchmarkSnapshot:
    global _CACHE
    cache_file = _cache_path()
    root = _resolve_gate_root()
    pdfs = [
        p
        for p in sorted(set(root.rglob("*.pdf")) | set(root.rglob("*.PDF")))
        if should_index_pdf(str(p))
    ]

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
        or (time.time() - cache_file.stat().st_mtime)
        > settings.GATE_BENCHMARK_MAX_AGE_HOURS * 3600
    )
    if rebuild_if_stale and stale and settings.ENABLE_GATE_BENCHMARK:
        return build_gate_benchmark()
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            _CACHE = data
            return _from_dict(data)
        except Exception as exc:
            logger.warning("GATE benchmark cache read failed: %s", exc)
    if settings.ENABLE_GATE_BENCHMARK and pdfs:
        return build_gate_benchmark()
    snap = BenchmarkSnapshot(source_root=str(root))
    snap.bands["gate"] = _boost_gate_profile(_profile_from_rule_packs("senior"))
    return snap


def gate_profile() -> BandProfile:
    return load_gate_benchmark().bands.get("gate") or _boost_gate_profile(
        _profile_from_rule_packs("senior")
    )


def gate_level_active(
    *,
    exam_track: str = "board",
    ui_difficulty: str = "medium",
    difficulty_distribution: Any = None,
    full_hard: bool = False,
    instructions: str = "",
) -> bool:
    """True when generated stems must meet GATE_QuestionPapers benchmark floors."""
    if not settings.ENABLE_GATE_BENCHMARK:
        return False
    if (exam_track or "").lower() == "gate":
        return True
    if full_hard:
        return bool(settings.ENABLE_GATE_LEVEL_FOR_HARD)
    if difficulty_distribution and settings.ENABLE_GATE_LEVEL_FOR_HARD:
        from app.generation.full_hard_mode import is_full_hard_paper

        if is_full_hard_paper(difficulty_distribution):
            return True
    if settings.ENABLE_GATE_LEVEL_FOR_HARD and (ui_difficulty or "").lower() == "hard":
        return True
    blob = (instructions or "").lower()
    if "gate" in blob and any(k in blob for k in ("level", "paper", "ma", "match")):
        return True
    return False


def _ensure_generation_scores(q: Dict[str, Any]) -> None:
    """Attach authenticity/combined scores when RAG apply skipped quality.score_batch."""
    if q.get("combined_score") and q.get("authenticity_score"):
        return
    from app.generation.cbse_benchmark import _score_stem_like_generation

    stem = {"content": q.get("content") or ""}
    scored = _score_stem_like_generation(stem)
    q.setdefault("authenticity_score", scored.get("authenticity_score", 0.5))
    q.setdefault("combined_score", scored.get("combined_score", 0.5))


def evaluate_against_gate(q: Dict[str, Any], *, slot_band: str = "L4") -> Dict[str, Any]:
    if not settings.ENABLE_GATE_BENCHMARK:
        return {"gate_enabled": False}
    prof = gate_profile()
    import re

    _ensure_generation_scores(q)
    content = (q.get("content") or "").strip()
    n_words = len(content.split())
    flags: List[str] = []
    score = 0.68
    band = (slot_band or "L4").upper()
    min_words = prof.min_word_count_soft
    if band == "L5":
        min_words = max(min_words, prof.word_count_p25 * 0.95)
    if n_words < min_words:
        flags.append("below_gate_stem_length")
        score -= 0.14
    elif n_words >= prof.target_word_count * 0.55:
        score += 0.1
    auth = float(q.get("authenticity_score") or 0)
    comb = float(q.get("combined_score") or 0)
    if auth < prof.min_authenticity_floor:
        flags.append("below_gate_authenticity_floor")
        score -= 0.12
    if comb < prof.min_combined_floor:
        flags.append("below_gate_combined_floor")
        score -= 0.14
    if not re.search(
        r"\bfind\b|\bprove\b|\bcalculate\b|\bevaluate\b|\bsolve\b|\bif\b|\bhence\b",
        content.lower(),
    ):
        flags.append("missing_gate_exam_verb")
        score -= 0.08
    stem_fmt = (q.get("stem_format") or "").strip()
    from app.generation.stem_pattern_variety import (
        pattern_forbids_subparts,
        validate_question_stem_pattern,
    )

    if stem_fmt:
        ok_pat, pat_flags = validate_question_stem_pattern(content, stem_fmt)
        if not ok_pat:
            flags.extend(pat_flags)
            score -= 0.12
    elif band in ("L4", "L5") and not re.search(
        r"\([ivx]+\)|\([a-z]\)|\([0-9]+\)",
        content,
        re.I,
    ):
        # Legacy: only when no per-slot pattern assigned
        if not pattern_forbids_subparts(stem_fmt or ""):
            flags.append("missing_gate_subparts")
            score -= 0.08
    marks = float(q.get("marks") or 0)
    if band == "L5" and marks > 0 and marks < max(4.0, prof.marks_median):
        flags.append("below_gate_marks_weight")
        score -= 0.06
    above = (
        n_words >= min_words
        and comb >= prof.combined_p75
        and "below_gate_combined_floor" not in flags
        and "missing_gate_subparts" not in flags
        and "unexpected_subparts" not in flags
        and "too_many_subparts_for_ii_pattern" not in flags
        and "missing_ii_parts" not in flags
        and "missing_iii_parts" not in flags
    )
    return {
        "gate_enabled": True,
        "gate_alignment_score": round(max(0.0, min(1.0, score)), 3),
        "gate_above_level": above,
        "gate_flags": flags,
        "gate_min_combined_floor": prof.min_combined_floor,
        "gate_target_words": prof.target_word_count,
        "gate_sample_count": prof.sample_count,
        "gate_reject": bool(flags) and not above,
    }


def validate_paper_against_gate(
    questions: List[Dict[str, Any]],
    *,
    ui_difficulty: str = "medium",
    slot_metadata: Optional[List[Dict[str, Any]]] = None,
    exam_track: str = "board",
    difficulty_distribution: Any = None,
    full_hard: bool = False,
    instructions: str = "",
) -> Dict[str, Any]:
    """Paper-level GATE alignment — used on apply-rag and generation QA."""
    active = gate_level_active(
        exam_track=exam_track,
        ui_difficulty=ui_difficulty,
        difficulty_distribution=difficulty_distribution,
        full_hard=full_hard,
        instructions=instructions,
    )
    if not active:
        return {"gate_paper_ok": True, "gate_paper_flags": [], "gate_level_active": False}
    prof = gate_profile()
    from app.generation.stem_pattern_variety import validate_paper_stem_variety

    patterns = [q.get("stem_format") or "" for q in questions]
    variety = validate_paper_stem_variety(questions, slot_patterns=patterns)
    flags: List[str] = list(variety.get("stem_variety_flags") or [])
    for i, q in enumerate(questions):
        meta = (slot_metadata or [{}])[i] if i < len(slot_metadata or []) else {}
        band = (meta.get("band") or q.get("slot_band") or "L4").upper()
        if full_hard:
            band = "L5"
        rep = evaluate_against_gate(q, slot_band=band)
        q.update({k: v for k, v in rep.items() if k.startswith("gate_")})
        if rep.get("gate_reject"):
            stem = (q.get("content") or "")[:100]
            flags.append(
                f"Q{i + 1} ({','.join(rep.get('gate_flags') or [])}): {stem}"
            )
    return {
        "gate_paper_ok": len(flags) == 0,
        "gate_paper_flags": flags,
        "gate_level_active": True,
        "gate_target_words": prof.target_word_count,
        "gate_min_combined_floor": prof.min_combined_floor,
        "stem_variety_ok": variety.get("stem_variety_ok", True),
    }


def apply_gate_benchmark_to_questions(
    questions: List[Dict[str, Any]],
    *,
    gate_active: bool = True,
) -> List[Dict[str, Any]]:
    if not settings.ENABLE_GATE_BENCHMARK or not gate_active:
        return questions
    for q in questions:
        rep = evaluate_against_gate(q)
        q.update(rep)
        if rep.get("gate_above_level"):
            q["combined_score"] = round(
                min(1.0, float(q.get("combined_score", 0)) + 0.06), 3
            )
        elif rep.get("gate_reject"):
            q["combined_score"] = round(
                max(0.0, float(q.get("combined_score", 0)) - 0.1), 3
            )
    return questions


def get_gate_combined_floor() -> float:
    if not settings.ENABLE_GATE_BENCHMARK:
        return 0.0
    return gate_profile().min_combined_floor


def gate_benchmark_prompt_hints(*, gate_active: bool = True) -> str:
    if not settings.ENABLE_GATE_BENCHMARK or not gate_active:
        return ""
    prof = gate_profile()
    if prof.sample_count < 1:
        return ""
    return (
        f"GATE PAPER LEVEL ({prof.sample_count} indexed GATE MA stems): "
        f"match postgraduate aptitude — stems ~{int(prof.word_count_p50)}–{int(prof.word_count_p75)} words "
        f"(target {int(prof.target_word_count)}); mandatory (i)(ii) sub-parts on L4/L5 slots; "
        f"prove+Hence or evaluate chains; marks ≥ {max(4, int(prof.marks_median))} on HOTS slots; "
        f"combined authenticity floor ≥ {prof.min_combined_floor:.2f}; "
        f"no Class-10 one-liner drills."
    )
