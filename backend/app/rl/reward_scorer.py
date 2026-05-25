"""
Heuristic + feedback-learned reward for generated questions.

Blends into combined_score when ENABLE_RL_REWARD is on (no torch required).
Optional transformer path via ENABLE_RL_TRANSFORMER.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.generation.textbook_constants import BANNED_META_PHRASES
from app.rl.feedback_collector import FeedbackCollector

logger = logging.getLogger(__name__)

_TRANSFORMER = None


def _load_tag_weights() -> Dict[str, float]:
    path = Path(settings.RL_TAG_WEIGHT_PATH)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_tag_weights(weights: Dict[str, float]) -> None:
    path = Path(settings.RL_TAG_WEIGHT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(weights, indent=2), encoding="utf-8")


def update_tag_weights_from_feedback(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Map negative tags → penalty, positive → boost (running average)."""
    tag_sums: Dict[str, List[float]] = {}
    for entry in entries:
        rating = float(entry.get("rating") or 3)
        norm = (rating - 1.0) / 4.0
        for tag in entry.get("tags") or []:
            tag_sums.setdefault(tag.lower(), []).append(norm)
    weights: Dict[str, float] = {}
    for tag, vals in tag_sums.items():
        avg = sum(vals) / len(vals)
        weights[tag] = round(avg - 0.5, 3)
    if weights:
        _save_tag_weights(weights)
    return weights


class RewardScorer:
    def __init__(self):
        self._tag_weights = _load_tag_weights()
        self._transformer = None

    def refresh_weights(self) -> None:
        entries = FeedbackCollector().load_entries(limit=2000)
        if entries:
            self._tag_weights = update_tag_weights_from_feedback(entries)
        else:
            self._tag_weights = _load_tag_weights()

    def _heuristic_score(self, q: Dict[str, Any]) -> float:
        stem = (q.get("content") or q.get("question") or "").strip()
        if not stem:
            return 0.0
        score = 0.55
        low = stem.lower()
        words = len(stem.split())
        if 12 <= words <= 55:
            score += 0.12
        elif words < 8:
            score -= 0.15
        elif words > 70:
            score -= 0.08

        for banned in BANNED_META_PHRASES:
            if banned.lower() in low:
                score -= 0.18

        if q.get("completeness_ok") is False:
            score -= 0.2
        if q.get("numeric_consistency_ok") is False:
            score -= 0.15
        if q.get("topic_drift"):
            score -= 0.25
        if q.get("authenticity_score", 0) >= 0.7:
            score += 0.08
        if q.get("reasoning_depth_score", 0) >= 0.65:
            score += 0.06

        for cmd in ("find ", "prove that", "show that", "if ", "calculate"):
            if cmd in low:
                score += 0.04
                break

        flags = q.get("quality_flags") or q.get("hard_mode_flags") or []
        for flag in flags:
            f = str(flag).lower()
            if "reject" in f or "missing" in f or "contamination" in f:
                score -= 0.12

        return max(0.0, min(1.0, score))

    def _feedback_tag_adjust(self, tags: List[str]) -> float:
        if not self._tag_weights:
            return 0.0
        adj = 0.0
        for tag in tags:
            adj += self._tag_weights.get(tag.lower(), 0.0) * 0.08
        return max(-0.2, min(0.2, adj))

    def _transformer_score(self, stem: str, answer: str) -> Optional[float]:
        if not settings.ENABLE_RL_TRANSFORMER:
            return None
        global _TRANSFORMER
        model_path = Path(settings.RL_TRANSFORMER_MODEL_PATH)
        if not model_path.exists():
            return None
        try:
            if _TRANSFORMER is None:
                from transformers import (
                    AutoModelForSequenceClassification,
                    AutoTokenizer,
                )

                tok = AutoTokenizer.from_pretrained(str(model_path))
                model = AutoModelForSequenceClassification.from_pretrained(
                    str(model_path), num_labels=1
                )
                model.eval()
                _TRANSFORMER = (tok, model)
            tok, model = _TRANSFORMER
            text = f"Question: {stem}\nAnswer: {answer}"
            enc = tok(text, return_tensors="pt", truncation=True, max_length=384)
            import torch

            with torch.no_grad():
                out = model(**enc)
                prob = torch.sigmoid(out.logits).item()
            return prob
        except Exception as exc:
            logger.warning("RL transformer score unavailable: %s", exc)
            return None

    def score_question(self, q: Dict[str, Any], *, feedback_tags: Optional[List[str]] = None) -> float:
        h = self._heuristic_score(q)
        tags = feedback_tags or []
        tag_adj = self._feedback_tag_adjust(tags)
        stem = q.get("content") or q.get("question") or ""
        answer = q.get("correct_answer") or ""
        if isinstance(answer, dict):
            answer = answer.get("text") or json.dumps(answer)[:500]
        t = self._transformer_score(str(stem), str(answer))
        if t is not None:
            return round(0.5 * h + 0.35 * t + 0.15 * (0.5 + tag_adj), 3)
        return round(max(0.0, min(1.0, h + tag_adj)), 3)


def apply_rl_reward(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not settings.ENABLE_RL_REWARD or not questions:
        return questions
    scorer = RewardScorer()
    scorer.refresh_weights()
    w = settings.RL_REWARD_WEIGHT
    for q in questions:
        rl = scorer.score_question(q)
        q["rl_reward_score"] = rl
        base = q.get("combined_score", q.get("quality_score", 0))
        q["combined_score"] = round((1.0 - w) * base + w * rl, 3)
    return questions
