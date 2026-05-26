"""
Reasoning depth scoring — inference chain length, not just theorem labels.

Separates coverage (which topics appear) from cognitive topology (how deep the chain is).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_STEP_RE = re.compile(r"\bstep\s*\d+\b", re.I)
_HENCE_RE = re.compile(r"\bhence\b|\btherefore\b|\bthus\b", re.I)
_REJECT_RE = re.compile(r"\breject\b|\bdiscard\b|\bextraneous\b", re.I)
_OR_STEM_RE = re.compile(r"\s+or\s+|\*\*or\*\*", re.I)
_SUBPART_RE = re.compile(r"\([iI]{1,3}[′']?\)|\([iv]{1,3}\)", re.I)
_PARAM_RE = re.compile(r"\bparameter\s+\w\b|\bfind\s+k\b|Δ\s*=|discriminant", re.I)
_WORD_MODEL_RE = re.compile(
    r"\bform\s+(?:an?\s+)?equation\b|\breduce\s+to\b|\bquadratic\s+in\b",
    re.I,
)
_FORMULA_RE = re.compile(r"quadratic\s+formula|−b\s*±|\+√", re.I)
_CONTRADICTION_RE = re.compile(r"\bcontradiction\b|\bimpossible\b|\bcannot\s+be\b", re.I)


def _answer_text(q: Dict[str, Any]) -> str:
    return (q.get("correct_answer") or q.get("answer") or "").strip()


def _count_inference_layers(answer: str, stem: str) -> int:
    layers = 0
    if _STEP_RE.findall(answer):
        layers += len(_STEP_RE.findall(answer))
    else:
        layers += len(re.findall(r"[.;]\s+", answer)) // 2
    layers += len(_HENCE_RE.findall(answer))
    layers += len(_REJECT_RE.findall(answer))
    layers += 1 if _FORMULA_RE.search(answer) else 0
    layers += 1 if _CONTRADICTION_RE.search(answer) else 0
    if _WORD_MODEL_RE.search(stem):
        layers += 2
    if _PARAM_RE.search(stem):
        layers += 1
    if _OR_STEM_RE.search(stem):
        layers += 1
    if _SUBPART_RE.search(stem):
        layers += len(_SUBPART_RE.findall(stem))
    return max(1, layers)


def reasoning_depth_score(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
) -> Dict[str, Any]:
    """
    Score 0–1: shallow factorise→solve vs deep parameter/discriminant/OR chains.
    """
    stem = (q.get("content") or "").strip()
    answer = _answer_text(q)
    flags: List[str] = []
    layers = _count_inference_layers(answer, stem)

    ui = (ui_difficulty or "medium").lower()
    band = (slot_band or "L3").upper()

    if band in ("L4", "L5") or ui in ("hard", "difficult"):
        min_layers = 4 if band == "L5" else 3
    elif band == "L3":
        min_layers = 2
    else:
        min_layers = 1

    if layers < min_layers:
        flags.append(f"solution_too_shallow:{band}_needs_L{min_layers}")

    # Trivial perfect-square only on hard L5
    if band == "L5" and ui in ("hard", "difficult"):
        if re.search(r"Δ\s*=\s*0", answer) and not _OR_STEM_RE.search(stem):
            if not _WORD_MODEL_RE.search(stem) and not _PARAM_RE.search(stem):
                flags.append("hots_lacks_fusion_depth")

    if _WORD_MODEL_RE.search(stem) and layers < 4 and band in ("L4", "L5"):
        flags.append("word_model_shallow_chain")

    # Map layers to score
    depth_ratio = min(1.0, layers / max(min_layers, 1))
    penalty = 0.15 * len(flags)
    score = max(0.0, min(1.0, 0.35 + 0.65 * depth_ratio - penalty))

    return {
        "reasoning_depth_score": round(score, 3),
        "reasoning_depth_layers": layers,
        "reasoning_depth_flags": flags,
        "reasoning_depth_ok": score >= 0.48
        and "solution_too_shallow" not in " ".join(flags),
    }


def should_reject_shallow_reasoning(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
    full_hard: bool = False,
) -> bool:
    if "reasoning_depth_score" not in q:
        q.update(reasoning_depth_score(q, slot_band=slot_band, ui_difficulty=ui_difficulty))
    if (ui_difficulty or "").lower() not in ("hard", "difficult"):
        return False
    band = (slot_band or "L3").upper()
    if band not in ("L4", "L5"):
        return False
    flags = q.get("reasoning_depth_flags") or []
    if any("solution_too_shallow" in f for f in flags):
        return True
    if "hots_lacks_fusion_depth" in flags:
        return True
    min_score = 0.55 if full_hard else 0.42
    if band == "L5" and q.get("reasoning_depth_score", 1) < min_score:
        return True
    if full_hard:
        stem = (q.get("content") or q.get("question") or "").strip()
        from app.generation.topic_isolation import get_current_topic_state

        ch = (get_current_topic_state() or {}).get("locked_chapter", "")
        if ch == "quadratic" and q.get("stem_quality_ok"):
            return False
        if len(stem.split()) < 28 and not re.search(
            r"\(i\)|\(ii\)|\(a\)|\(b\)|\bor\b", stem, re.I
        ):
            return True
    return False
