"""
Train tag weights + optional sklearn regressor from feedback.jsonl.

Usage (from backend/):
  python scripts/train_rl_reward.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rl.feedback_collector import FeedbackCollector
from app.rl.reward_scorer import update_tag_weights_from_feedback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    entries = FeedbackCollector().load_entries()
    if len(entries) < 3:
        logger.warning("Need at least 3 feedback rows; found %d", len(entries))
        return
    weights = update_tag_weights_from_feedback(entries)
    logger.info("Updated %d tag weights", len(weights))
    try:
        import numpy as np
        from sklearn.feature_extraction.text import HashingVectorizer
        from sklearn.linear_model import Ridge
        import joblib

        texts, y = [], []
        for e in entries:
            meta = e.get("metadata") or {}
            texts.append(meta.get("question") or "")
            y.append((float(e.get("rating") or 3) - 1.0) / 4.0)
        if len(texts) >= 5:
            vec = HashingVectorizer(n_features=256)
            X = vec.fit_transform(texts)
            model = Ridge(alpha=1.0).fit(X, y)
            out = Path("./data/rl/sklearn_reward.joblib")
            out.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({"vectorizer": vec, "model": model}, out)
            logger.info("Saved sklearn reward to %s", out)
    except ImportError:
        logger.info("sklearn not installed — tag weights only")


if __name__ == "__main__":
    main()
