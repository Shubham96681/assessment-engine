"""
Chapter paper quality — generic validators driven by ChapterRulePack + archetype metadata.

No chapter-specific tables in this module. Register rules on ChapterRulePack.paper_quality
and skill_family / marks_min / marks_max on archetype definitions in rd_archetypes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.generation.archetype_registry import (
    archetype_definitions_for_chapter,
    infer_archetype_from_stem,
    normalize_archetype_id,
)
from app.generation.chapter_rule_packs import (
    ChapterPaperQualityConfig,
    ChapterRulePack,
    SlotPlanRow,
    get_chapter_rule_pack,
)


@dataclass(frozen=True)
class MarkBand:
    min_marks: int
    max_marks: int


@dataclass
class ChapterPaperQualitySpec:
    """Runtime view built from rule pack + archetype registry."""

    chapter_key: str
    config: ChapterPaperQualityConfig
    archetype_mark_bands: Dict[str, MarkBand]
    skill_family_by_archetype: Dict[str, str]
    max_per_skill_family: Dict[str, int]
    slot_sequences: Dict[int, Tuple[SlotPlanRow, ...]]


def _mark_band_from_arch(arch: Dict[str, str]) -> Optional[MarkBand]:
    try:
        lo = int(str(arch.get("marks_min", "")).strip())
        hi = int(str(arch.get("marks_max", "")).strip())
    except (TypeError, ValueError):
        return None
    if lo <= 0 or hi <= 0 or hi < lo:
        return None
    return MarkBand(lo, hi)


def spec_from_rule_pack(pack: ChapterRulePack) -> Optional[ChapterPaperQualitySpec]:
    cfg = pack.paper_quality
    if not cfg or not cfg.enabled:
        return None
    mark_bands: Dict[str, MarkBand] = {}
    families: Dict[str, str] = {}
    for arch in archetype_definitions_for_chapter(pack.chapter_key):
        aid = arch.get("id", "")
        if not aid:
            continue
        band = _mark_band_from_arch(arch)
        if band:
            mark_bands[aid] = band
        fam = (arch.get("skill_family") or "").strip()
        if fam:
            families[aid] = fam
    slot_sequences: Dict[int, Tuple[SlotPlanRow, ...]] = {}
    for count, rows in cfg.slot_plans:
        slot_sequences[int(count)] = tuple(rows)
    return ChapterPaperQualitySpec(
        chapter_key=pack.chapter_key,
        config=cfg,
        archetype_mark_bands=mark_bands,
        skill_family_by_archetype=families,
        max_per_skill_family=cfg.max_family_dict(),
        slot_sequences=slot_sequences,
    )


def _issue_matches_tokens(issue: str, tokens: Sequence[str]) -> bool:
    return any(token in issue for token in tokens if token)


def _flag_matches_prefixes(flag: str, prefixes: Sequence[str]) -> bool:
    return any(
        flag.startswith(prefix) or flag == prefix
        for prefix in prefixes
        if prefix
    )


def get_chapter_quality_spec(chapter: str) -> Optional[ChapterPaperQualitySpec]:
    return spec_from_rule_pack(get_chapter_rule_pack(chapter))


def validate_all_slots_present(
    questions: List[Dict[str, Any]],
    expected_count: int,
) -> Tuple[bool, List[str]]:
    """Every slot 1..N must exist with non-empty stem (prevents blank PDF lines)."""
    by_slot: Dict[int, Dict[str, Any]] = {}
    for q in questions:
        try:
            sn = int(q.get("slot_number") or q.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if sn >= 1:
            by_slot[sn] = q
    issues: List[str] = []
    for slot in range(1, expected_count + 1):
        q = by_slot.get(slot)
        stem = ""
        if q:
            stem = (q.get("content") or q.get("question") or "").strip()
        if not stem:
            issues.append(f"missing_or_empty_slot:{slot}")
    return (not issues, issues)


def planned_archetype_ids(
    chapter: str,
    question_count: int,
    *,
    ui_difficulty: str = "medium",
) -> List[str]:
    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return []
    seq = spec.slot_sequences.get(question_count)
    if seq:
        return [e.archetype_id for e in seq]
    base = spec.slot_sequences.get(5)
    if not base:
        return []
    ids: List[str] = []
    fam_count: Dict[str, int] = {}
    idx = 0
    while len(ids) < question_count:
        entry = base[idx % len(base)]
        fam = spec.skill_family_by_archetype.get(entry.archetype_id, entry.archetype_id)
        cap = spec.max_per_skill_family.get(fam, 99)
        if fam_count.get(fam, 0) >= cap:
            idx += 1
            if idx > question_count * 4:
                break
            continue
        ids.append(entry.archetype_id)
        fam_count[fam] = fam_count.get(fam, 0) + 1
        idx += 1
    return ids


def expand_sequence_slots(
    chapter: str,
    question_count: int,
    *,
    ui_difficulty: str = "medium",
    full_hard: bool = False,
) -> List[Dict[str, Any]]:
    ch = (chapter or "").strip().lower()
    if full_hard and ch == "trigonometry":
        from app.generation.trigonometry_hard_benchmark import benchmark_slots

        return benchmark_slots(question_count)
    if full_hard and ch == "quadratic":
        from app.generation.quadratic_hard_benchmark import benchmark_slots

        return benchmark_slots(question_count)
    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return []
    seq = spec.slot_sequences.get(question_count)
    if not seq:
        seq = spec.slot_sequences.get(5)
    if not seq:
        return []
    pack = get_chapter_rule_pack(chapter)
    slots: List[Dict[str, Any]] = []
    for i in range(question_count):
        entry = seq[i] if i < len(seq) else seq[i % len(seq)]
        cog = (
            pack.cognitive_blueprint_5[i]
            if i < len(pack.cognitive_blueprint_5)
            else pack.cognitive_blueprint_5[-1]
        )
        band = "L5" if full_hard else entry.band
        d: Dict[str, Any] = {
            "slot": i + 1,
            "band": band,
            "role": entry.role or cog,
            "archetype_id": entry.archetype_id,
            "cognitive_type": cog,
            "one_line_ok": False if full_hard else entry.band in ("L1", "L2"),
        }
        if entry.max_marks is not None:
            d["max_marks"] = entry.max_marks
        if i == 1:
            d["memory"] = "teach"
        if i == question_count - 1:
            d["memory"] = "reuse"
        if entry.band == "L5":
            d["sparse_hard"] = True
        slots.append(d)
    return slots


def _format_mark_bullets(spec: ChapterPaperQualitySpec) -> str:
    parts: List[str] = []
    for aid in get_chapter_rule_pack(spec.chapter_key).archetype_ids:
        band = spec.archetype_mark_bands.get(aid)
        if band:
            parts.append(f"{aid} {band.min_marks}–{band.max_marks}")
    return "; ".join(parts)


def chapter_paper_quality_prompt_block(
    chapter: str,
    question_count: int = 10,
    *,
    ui_difficulty: str = "medium",
    full_hard: bool = False,
) -> str:
    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return ""
    pack = get_chapter_rule_pack(chapter)
    lines = [f"PAPER QUALITY — {pack.display_title}:"]
    for fam, cap in spec.max_per_skill_family.items():
        lines.append(f"- Max {cap} item(s) with skill family '{fam}'.")
    mark_line = _format_mark_bullets(spec)
    if mark_line:
        lines.append(f"- Marks by archetype: {mark_line}.")
    for bullet in spec.config.prompt_bullets:
        lines.append(f"- {bullet}")
    if spec.config.standard_exact_degree_step > 0:
        step = spec.config.standard_exact_degree_step
        lines.append(
            f"- Exact surd angles: multiples of {step}° after reduction only."
        )
    seq = expand_sequence_slots(
        chapter,
        question_count,
        ui_difficulty=ui_difficulty,
        full_hard=full_hard,
    )
    if seq:
        lines.append("- Slot archetype plan (follow ids):")
        for s in seq[:question_count]:
            mm = f", max {s['max_marks']} marks" if s.get("max_marks") else ""
            lines.append(
                f'  id "{s["slot"]}": [{s.get("archetype_id")}] band {s["band"]}{mm} — {s.get("role", "")}'
            )
    return "\n".join(lines)


def _stem(q: Dict[str, Any]) -> str:
    return (q.get("content") or q.get("question") or "").strip()


def _resolve_archetype_id(
    q: Dict[str, Any],
    spec: ChapterPaperQualitySpec,
) -> str:
    raw = (q.get("archetype_id") or q.get("slot_archetype") or "").strip()
    if raw:
        return normalize_archetype_id(raw, spec.chapter_key)
    pack = get_chapter_rule_pack(spec.chapter_key)
    return infer_archetype_from_stem(_stem(q), pack.archetype_ids)


def _parse_degree_angles(stem: str) -> List[float]:
    angles: List[float] = []
    patterns = (
        r"(\d{1,4})\s*°\s*(\d{1,2})?\s*['′]?",
        r"(\d{1,4})\s*(?:°|deg(?:rees?)?)\s*(\d{1,2})\s*(?:['′]|min(?:utes?)?)?",
        r"(\d{1,4})\s*°\s*(\d{1,2})\s*['′]",
    )
    seen: set[float] = set()
    for pat in patterns:
        for m in re.finditer(pat, stem, re.I):
            deg = float(m.group(1))
            mins = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            if mins:
                deg += float(mins) / 60.0
            if deg not in seen:
                seen.add(deg)
                angles.append(deg)
    return angles


def _is_standard_exact_degree(deg: float, step: int) -> bool:
    if step <= 0:
        return True
    norm = deg % 360.0
    if abs(norm) < 0.01 or abs(norm - 360.0) < 0.01:
        return True
    rem = norm % step
    return abs(rem) < 0.02 or abs(rem - step) < 0.02


def _stem_requests_exact_surd(stem: str) -> bool:
    low = stem.lower()
    return bool(
        re.search(r"\bexact\b", low)
        and re.search(r"\b(surd|sin|cos|tan|value)\b", low)
    )


def _or_branch_scores(stem: str, weights) -> Tuple[List[float], List[str]]:
    parts = re.split(r"\s+\bOR\b\s+", stem, flags=re.I)
    if len(parts) < 2:
        return [], []
    scores: List[float] = []
    for part in parts:
        low = part.lower()
        s = 1.0
        if re.search(r"\bprove\b", low):
            s += weights.prove
        if re.search(r"\b(sin|cos|tan)\s*\(\s*[a-z]\s*[-+]", low):
            s += weights.compound_identity
        if re.search(r"\breduce\b", low) and not re.search(r"\bprove\b", low):
            s += weights.reduction_only
        if re.search(
            r"\b(find|value of)\s+(sin|cos|tan|sec|cosec|cot)\s*\(\s*-?\s*\d{3,}",
            low,
        ):
            s += weights.large_angle_reduction
        scores.append(s)
    return scores, parts


def validate_exact_angle_choice(stem: str, spec: ChapterPaperQualitySpec) -> List[str]:
    flags: List[str] = []
    cfg = spec.config
    if not stem or cfg.standard_exact_degree_step <= 0:
        return flags
    step = cfg.standard_exact_degree_step
    if cfg.forbid_minute_with_exact_surd and _stem_requests_exact_surd(stem):
        if re.search(
            r"\d+\s*(?:°|deg)\s*\d{1,2}\s*(?:['′]|min\b)",
            stem,
            re.I,
        ) or re.search(r"\d+\s*°\s*\d{1,2}\s*['′]", stem):
            flags.append("exact_surd_with_minute_angle")
        for deg in _parse_degree_angles(stem):
            if not _is_standard_exact_degree(deg, step) and _stem_requests_exact_surd(stem):
                flags.append(f"non_standard_exact_angle:{deg:g}°")
    return flags


def _proof_route_check_text(stem: str, correct_answer: str) -> str:
    return f"{stem or ''}\n{correct_answer or ''}"


def _matches_sin_ab_route(text: str) -> bool:
    """sin(A±B) family — not bare 'sin(a' substring false positives."""
    return bool(
        re.search(r"sin\s*\(\s*a\s*[-−+]", text, re.I)
        or re.search(r"sin\s*\(\s*a\s*\+\s*b", text, re.I)
        or re.search(r"sin\s*\(\s*a\s*[-−]\s*b", text, re.I)
    )


def _matches_cos_ab_route(text: str) -> bool:
    return bool(
        re.search(r"cos\s*\(\s*a\s*[-−+]", text, re.I)
        or re.search(r"cos\s*\(\s*a\s*\+\s*b", text, re.I)
        or re.search(r"cos\s*\(\s*a\s*[-−]\s*b", text, re.I)
    )


def validate_proof_route(
    stem: str,
    spec: ChapterPaperQualitySpec,
    *,
    archetype_id: str = "",
    correct_answer: str = "",
) -> List[str]:
    """
    Identity proof route checks — only for prove stems (or identity_prove archetype).
    Stem needle must match; required/forbidden formulas checked in stem + model answer.
    """
    flags: List[str] = []
    stem_low = (stem or "").lower()
    if archetype_id and archetype_id not in ("identity_prove", ""):
        return flags
    if "prove" not in stem_low and archetype_id != "identity_prove":
        return flags
    check = _proof_route_check_text(stem, correct_answer).lower()
    for rule in spec.config.proof_route_rules:
        needle = rule.stem_needle.lower()
        if needle not in stem_low and not re.search(needle, stem_low, re.I):
            continue
        req = (rule.required_phrase or "").lower()
        if req in ("sin(a", "sin (a"):
            if not _matches_sin_ab_route(check):
                flags.append(f"proof_route_missing:{rule.required_phrase}")
        elif req and req not in check:
            flags.append(f"proof_route_missing:{rule.required_phrase}")
        forb = (rule.forbidden_phrase or "").lower()
        if forb in ("cos(a", "cos (a"):
            if _matches_cos_ab_route(check):
                flags.append(f"proof_route_wrong_formula:{rule.forbidden_phrase}")
        elif forb and forb in check:
            flags.append(f"proof_route_wrong_formula:{rule.forbidden_phrase}")
    return flags


def validate_stem_pattern_caps(
    questions: List[Dict[str, Any]],
    spec: ChapterPaperQualitySpec,
) -> List[str]:
    flags: List[str] = []
    for cap in spec.config.stem_pattern_caps:
        count = 0
        for q in questions:
            stem = (_stem(q) or "").lower()
            if re.search(cap.pattern, stem, re.I):
                count += 1
        if count > cap.max_count:
            flags.append(f"stem_pattern_excess:{cap.pattern}:{count}>{cap.max_count}")
    return flags


def validate_or_balance(stem: str, spec: ChapterPaperQualitySpec) -> List[str]:
    ratio_cap = spec.config.max_or_difficulty_ratio
    if ratio_cap <= 0:
        return []
    scores, _ = _or_branch_scores(stem, spec.config.or_branch_weights)
    if len(scores) < 2:
        return []
    hi, lo = max(scores), min(scores)
    if lo < 0.01:
        return ["or_branch_trivial"]
    if hi / lo > ratio_cap:
        return [f"or_branch_imbalance:{hi:.1f}/{lo:.1f}"]
    return []


def validate_marks_for_archetype(
    marks: int,
    archetype_id: str,
    spec: ChapterPaperQualitySpec,
    *,
    slot_max: Optional[int] = None,
) -> List[str]:
    flags: List[str] = []
    band = spec.archetype_mark_bands.get(archetype_id)
    if not band:
        return flags
    cap = slot_max if slot_max is not None else band.max_marks
    if marks > cap:
        flags.append(f"marks_inflated:{archetype_id}:{marks}>{cap}")
    if marks < band.min_marks:
        flags.append(f"marks_deflated:{archetype_id}:{marks}<{band.min_marks}")
    return flags


def annotate_chapter_paper_quality(
    questions: List[Dict[str, Any]],
    *,
    chapter: str,
) -> List[Dict[str, Any]]:
    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return questions
    fam_counts: Dict[str, int] = {}
    seq = spec.slot_sequences.get(len(questions)) or spec.slot_sequences.get(5)
    for i, q in enumerate(questions):
        stem = _stem(q)
        aid = _resolve_archetype_id(q, spec)
        q["archetype_id"] = q.get("archetype_id") or aid
        fam = spec.skill_family_by_archetype.get(aid, aid)
        fam_counts[fam] = fam_counts.get(fam, 0) + 1
        flags: List[str] = list(q.get("chapter_quality_flags") or [])
        if not stem.strip():
            flags.append("empty_stem")
        flags.extend(validate_exact_angle_choice(stem, spec))
        flags.extend(validate_or_balance(stem, spec))
        flags.extend(
            validate_proof_route(
                stem,
                spec,
                archetype_id=aid,
                correct_answer=str(q.get("correct_answer") or ""),
            )
        )
        try:
            mk = int(q.get("marks") or 0)
        except (TypeError, ValueError):
            mk = 0
        slot_cap: Optional[int] = None
        if seq and i < len(seq):
            slot_cap = seq[i].max_marks
        flags.extend(validate_marks_for_archetype(mk, aid, spec, slot_max=slot_cap))
        cap = spec.max_per_skill_family.get(fam)
        if cap is not None and fam_counts[fam] > cap:
            flags.append(f"skill_family_cap:{fam}:{fam_counts[fam]}>{cap}")
        q["chapter_quality_flags"] = flags
        q["chapter_skill_family"] = fam
    return questions


def normalize_chapter_paper_marks(
    questions: List[Dict[str, Any]],
    *,
    chapter: str,
    full_hard: bool = False,
) -> List[Dict[str, Any]]:
    ch = (chapter or "").strip().lower()
    if full_hard and ch == "trigonometry" and questions:
        from app.generation.trigonometry_hard_benchmark import target_marks_for_slot

        n = len(questions)
        for i, q in enumerate(questions):
            q["marks"] = target_marks_for_slot(i + 1, n)
            q["marks_normalized"] = True
        return questions
    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return questions
    seq = spec.slot_sequences.get(len(questions)) or spec.slot_sequences.get(5)
    for i, q in enumerate(questions):
        aid = _resolve_archetype_id(q, spec)
        band = spec.archetype_mark_bands.get(aid)
        if not band:
            continue
        slot_cap: Optional[int] = None
        if seq and i < len(seq):
            slot_cap = seq[i].max_marks
        try:
            mk = int(q.get("marks") or 0)
        except (TypeError, ValueError):
            mk = band.max_marks
        hi = slot_cap if slot_cap is not None else band.max_marks
        lo = band.min_marks
        if mk > hi:
            q["marks"] = hi
            q["marks_normalized"] = True
        elif 0 < mk < lo:
            q["marks"] = lo
            q["marks_normalized"] = True
    return questions


def validate_chapter_paper_quality(
    questions: List[Dict[str, Any]],
    *,
    chapter: str,
) -> Dict[str, Any]:
    spec = get_chapter_quality_spec(chapter)
    if not spec:
        return {"chapter_quality_ok": True, "chapter_quality_flags": []}
    annotate_chapter_paper_quality(questions, chapter=chapter)
    issues: List[str] = list(validate_stem_pattern_caps(questions, spec))
    from app.generation.difficulty_escalation import validate_escalation_quality

    esc_ok, esc_issues = validate_escalation_quality(questions, chapter=chapter)
    if not esc_ok:
        issues.extend(esc_issues)
    for q in questions:
        slot = q.get("order_index") or q.get("slot_number") or q.get("id")
        for f in q.get("chapter_quality_flags") or []:
            if (
                q.get("marks_normalized")
                and (f.startswith("marks_inflated") or f.startswith("marks_deflated"))
            ):
                continue
            issues.append(f"slot{slot}:{f}")
    tokens = spec.config.critical_issue_tokens
    critical = (
        list(issues)
        if not tokens
        else [x for x in issues if _issue_matches_tokens(x, tokens)]
    )
    return {
        "chapter_quality_ok": len(critical) == 0,
        "chapter_quality_flags": issues,
        "chapter_quality_critical": critical,
    }


def should_reject_chapter_paper_quality(
    q: Dict[str, Any],
    *,
    chapter: str = "",
    paper_questions: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    from app.core.config import settings

    if not getattr(settings, "ENABLE_CHAPTER_PAPER_QUALITY", True):
        return False
    ch = (chapter or q.get("locked_chapter") or "").strip().lower()
    spec = get_chapter_quality_spec(ch)
    if not spec:
        return False
    siblings = paper_questions or []
    if siblings:
        annotate_chapter_paper_quality(siblings, chapter=ch)
    stem = _stem(q)
    flags: List[str] = []
    if not stem.strip():
        flags.append("empty_stem")
    flags.extend(validate_exact_angle_choice(stem, spec))
    flags.extend(validate_or_balance(stem, spec))
    aid = _resolve_archetype_id(q, spec)
    flags.extend(
        validate_proof_route(
            stem,
            spec,
            archetype_id=aid,
            correct_answer=str(q.get("correct_answer") or ""),
        )
    )
    try:
        mk = int(q.get("marks") or 0)
    except (TypeError, ValueError):
        mk = 0
    flags.extend(validate_marks_for_archetype(mk, aid, spec))
    reject_prefixes = spec.config.reject_flag_prefixes
    if reject_prefixes and any(
        _flag_matches_prefixes(f, reject_prefixes) for f in flags
    ):
        q["chapter_quality_flags"] = flags
        return True
    if siblings:
        fam = spec.skill_family_by_archetype.get(aid, aid)
        cap = spec.max_per_skill_family.get(fam)
        if cap is not None:
            count = sum(
                1
                for s in siblings
                if spec.skill_family_by_archetype.get(
                    _resolve_archetype_id(s, spec), ""
                )
                == fam
            )
            if count > cap:
                q["chapter_quality_flags"] = flags + [f"skill_family_cap:{fam}"]
                return True
    return False


def reasoning_diversity_ok_for_chapter(
    questions: List[Dict[str, Any]],
    *,
    chapter: str,
) -> Tuple[bool, str]:
    spec = get_chapter_quality_spec(chapter)
    if not spec or len(questions) < 2:
        return True, ""
    annotate_chapter_paper_quality(questions, chapter=chapter)
    for fam, cap in spec.max_per_skill_family.items():
        n = sum(1 for q in questions if q.get("chapter_skill_family") == fam)
        if n > cap:
            return False, f"chapter_skill_family_excess:{fam}:{n}>{cap}"
    reject_at = spec.config.max_marks_inflated_reject
    if reject_at > 0:
        inflated = sum(
            1
            for q in questions
            for f in (q.get("chapter_quality_flags") or [])
            if f.startswith("marks_inflated")
        )
        if inflated >= reject_at:
            return False, f"chapter_marks_inflated_count:{inflated}"
    if any(
        "or_branch" in f
        for q in questions
        for f in (q.get("chapter_quality_flags") or [])
    ):
        return False, "chapter_or_imbalance"
    return True, ""
