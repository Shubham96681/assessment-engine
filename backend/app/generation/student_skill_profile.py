"""
Adaptive paper planning from student skill profile (weak_in / strong_in).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def parse_skill_list(raw: Optional[str | List[str]]) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r"[,;\n]+", str(raw))
    return [re.sub(r"\s+", "_", x.strip().lower()) for x in items if x.strip()]


def match_theorem_to_skill(skill_token: str, theorem: Dict[str, str]) -> bool:
    tid = (theorem.get("id") or "").lower()
    label = (theorem.get("label") or "").lower()
    cog = (theorem.get("cognitive_type") or "").lower()
    arch = (theorem.get("archetype_id") or "").lower()
    token = skill_token.replace(" ", "_")
    blob = f"{tid} {label} {cog} {arch}"
    return token in blob or token.replace("_", " ") in blob


def apply_student_skill_profile(
    required_theorems: List[Dict[str, str]],
    *,
    weak_in: Optional[List[str]] = None,
    strong_in: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """
    Boost weight/importance for weak areas; deprioritize strong areas (still may appear once).
    """
    weak = weak_in or []
    strong = strong_in or []
    if not weak and not strong:
        return required_theorems

    adjusted: List[Dict[str, str]] = []
    for t in required_theorems:
        entry = dict(t)
        w = float(entry.get("weight", 0.85))
        imp = entry.get("importance", "important")

        for sk in weak:
            if match_theorem_to_skill(sk, entry):
                w = min(1.0, w + 0.2)
                imp = "required"
                entry["skill_target"] = "weak_reinforce"
                break

        for sk in strong:
            if match_theorem_to_skill(sk, entry):
                w = max(0.25, w - 0.25)
                if imp == "required":
                    imp = "important"
                entry["skill_target"] = "strong_light"
                break

        entry["weight"] = w
        entry["importance"] = imp
        adjusted.append(entry)

    rank = {"required": 0, "important": 1, "optional": 2, "bonus": 3}
    adjusted.sort(key=lambda x: (rank.get(x.get("importance", "important"), 2), -x.get("weight", 0)))
    return adjusted


def student_skill_prompt_block(
    *,
    weak_in: Optional[List[str]] = None,
    strong_in: Optional[List[str]] = None,
) -> str:
    weak = weak_in or []
    strong = strong_in or []
    if not weak and not strong:
        return ""
    lines = ["STUDENT SKILL TARGETING (diagnostic paper):"]
    if weak:
        lines.append(f"- Reinforce (more items, medium-hard): {', '.join(weak)}")
    if strong:
        lines.append(f"- Light touch only (avoid drilling): {', '.join(strong)}")
    lines.append("- Weak areas: proof + multi-step; strong areas: one short item max.")
    return "\n".join(lines) + "\n"
