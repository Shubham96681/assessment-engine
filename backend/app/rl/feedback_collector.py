"""
Append-only human feedback store (phyEngine-style JSONL).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class FeedbackCollector:
    def __init__(self, storage_path: Optional[str] = None):
        self.path = Path(storage_path or settings.RL_FEEDBACK_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_feedback(
        self,
        *,
        question_id: str = "",
        assessment_id: str = "",
        rating: float,
        tags: Optional[List[str]] = None,
        comment: str = "",
        question_text: str = "",
        answer_text: str = "",
        chapter: str = "",
        slot_index: int = -1,
        quality_flags: Optional[List[str]] = None,
        combined_score: float = 0.0,
    ) -> Dict[str, Any]:
        entry = {
            "ts": time.time(),
            "question_id": question_id,
            "assessment_id": assessment_id,
            "rating": float(rating),
            "tags": tags or [],
            "comment": (comment or "")[:500],
            "metadata": {
                "question": (question_text or "")[:2000],
                "answer": (answer_text or "")[:2000],
                "chapter": chapter,
                "slot_index": slot_index,
                "quality_flags": quality_flags or [],
                "combined_score": combined_score,
            },
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.debug("RL feedback recorded: rating=%.1f tags=%s", rating, tags)
        return entry

    def load_entries(self, limit: int = 5000) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows[-limit:]
