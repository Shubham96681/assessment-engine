"""
Tagged prompt sections — chapter-scoped assembly with compile-time guards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class PromptSection:
    """One compile unit; must match locked chapter unless category is global metadata."""

    chapter: str  # locked chapter key or "any" for system/contract lines
    category: str
    text: str

    def is_allowed_for(self, locked_chapter: str) -> bool:
        ch = (self.chapter or "any").strip().lower()
        locked = (locked_chapter or "generic").strip().lower()
        return ch in ("any", locked)


class PromptSectionGuardError(Exception):
    def __init__(self, locked_chapter: str, bad: List[PromptSection]):
        self.locked_chapter = locked_chapter
        self.bad = bad
        cats = ", ".join(f"{s.category}({s.chapter})" for s in bad[:6])
        super().__init__(
            f"Prompt section chapter mismatch for locked={locked_chapter}: {cats}"
        )


def filter_sections_by_chapter(
    sections: Sequence[PromptSection],
    locked_chapter: str,
) -> List[PromptSection]:
    """Drop sections that belong to another chapter universe."""
    locked = (locked_chapter or "generic").strip().lower()
    return [s for s in sections if s.is_allowed_for(locked)]


def assert_sections_match_chapter(
    sections: Sequence[PromptSection],
    locked_chapter: str,
    *,
    strict: bool = True,
) -> None:
    bad = [s for s in sections if not s.is_allowed_for(locked_chapter)]
    if bad and strict:
        raise PromptSectionGuardError(locked_chapter, bad)


def assemble_prompt(sections: Sequence[PromptSection]) -> str:
    return "\n\n".join(s.text.strip() for s in sections if s.text and s.text.strip())
