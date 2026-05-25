"""
Canonical archetype namespace — single source for rule packs, blueprint, validators, local fallback.

ChapterRulePack.archetype_ids is authoritative; rd_archetypes pools are filtered to this set.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

# Legacy planner ids → canonical (same chapter)
ARCHETYPE_ALIASES: Dict[str, str] = {
    "tangent_pair": "angle_theorem",
    "power_of_point": "secant_tangent",
    "concentric_chord": "concentric",
}


def get_chapter_pack(chapter: str):
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    return get_chapter_rule_pack(chapter)


def allowed_archetype_ids(chapter: str) -> Tuple[str, ...]:
    """Ids that may appear in blueprint, regeneration, and validation."""
    return get_chapter_pack(chapter).archetype_ids


def normalize_archetype_id(archetype_id: str, chapter: str = "generic") -> str:
    aid = (archetype_id or "").strip()
    if not aid:
        return aid
    allowed = set(allowed_archetype_ids(chapter))
    if aid in allowed:
        return aid
    mapped = ARCHETYPE_ALIASES.get(aid)
    if mapped and mapped in allowed:
        return mapped
    return aid


def is_allowed_archetype(archetype_id: str, chapter: str) -> bool:
    return normalize_archetype_id(archetype_id, chapter) in set(allowed_archetype_ids(chapter))


def filter_archetype_dicts(
    archetypes: List[Dict],
    chapter: str,
) -> List[Dict]:
    """Keep only chapter-allowed ids (used by pick_weighted_archetypes output)."""
    allowed = set(allowed_archetype_ids(chapter))
    out: List[Dict] = []
    for a in archetypes:
        aid = normalize_archetype_id(a.get("id", ""), chapter)
        if aid in allowed:
            b = dict(a)
            b["id"] = aid
            out.append(b)
    return out


def archetype_definitions_for_chapter(chapter: str) -> List[Dict[str, str]]:
    """Full metadata rows from rd_archetypes, restricted to allowed ids."""
    from app.generation.rd_archetypes import _chapter_archetype_pool

    allowed = set(allowed_archetype_ids(chapter))
    return [a for a in _chapter_archetype_pool(chapter) if a.get("id") in allowed]


def infer_archetype_from_stem(
    stem: str,
    allowed_ids: Sequence[str],
    *,
    chapter: str = "generic",
) -> str:
    """
    Score stem against allowed archetype stem_hint / example / id tokens — no chapter branches.
    """
    from app.generation.rd_archetypes import ARCHETYPE_BY_ID

    text = (stem or "").lower()
    if not text or not allowed_ids:
        return normalize_archetype_id(allowed_ids[0], chapter) if allowed_ids else ""

    best_id = ""
    best_score = -1
    for aid in allowed_ids:
        arch = ARCHETYPE_BY_ID.get(aid, {})
        if not arch:
            continue
        score = 0
        if aid.replace("_", " ") in text or aid in text:
            score += 2
        hint = (arch.get("stem_hint") or "").lower()
        example = (arch.get("example") or "").lower()
        for token in re.findall(r"[a-z]{4,}", f"{hint} {example}"):
            if token in text:
                score += 1
        if re.search(r"\bprove\b", text) and "prove" in hint:
            score += 3
        if re.search(r"\bconvert\b", text) and "convert" in hint:
            score += 3
        if re.search(r"\bquadrant\b", text) and "quadrant" in hint:
            score += 2
        if re.search(r"\breduce\b", text) and "reduce" in hint:
            score += 2
        if re.search(r"\bratio\b", text) and "ratio" in hint:
            score += 2
        if score > best_score:
            best_score = score
            best_id = aid
    return normalize_archetype_id(best_id or allowed_ids[0], chapter)


def validate_slot_archetypes(slots: List, chapter: str) -> List[str]:
    """Return warning messages for ids outside the canonical pool."""
    warnings: List[str] = []
    allowed = set(allowed_archetype_ids(chapter))
    for s in slots:
        aid = getattr(s, "archetype_id", None) or (s.get("archetype_id") if isinstance(s, dict) else "")
        norm = normalize_archetype_id(str(aid or ""), chapter)
        if norm and norm not in allowed:
            warnings.append(f"slot {getattr(s, 'slot', '?')}: archetype '{aid}' not in registry")
    return warnings
