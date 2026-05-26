"""
Build GATE quality benchmark from GATE_QuestionPapers/**/*.pdf

Usage (from backend/):
  python scripts/build_gate_benchmark.py [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.generation.gate_benchmark import build_gate_benchmark, load_gate_benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    snap = build_gate_benchmark(force=args.force)
    print(f"PDFs: {snap.pdf_count}, stems: {snap.stem_count}")
    prof = snap.bands.get("gate")
    if prof and prof.sample_count:
        print(
            f"  gate: n={prof.sample_count} "
            f"combined_floor={prof.min_combined_floor:.3f} "
            f"target_words={prof.target_word_count:.0f}"
        )
    load_gate_benchmark(rebuild_if_stale=False)


if __name__ == "__main__":
    main()
