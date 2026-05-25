"""
Build CBSE reference vector index (question stems by chapter/topic).

Usage (from backend/):
  python scripts/build_cbse_reference_index.py [--force]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    from app.generation.cbse_reference_ingest import build_cbse_reference_index

    man = await build_cbse_reference_index(force=args.force)
    print(f"status={man.get('status')} pdfs={man.get('pdf_count')} stems={man.get('stem_count')}")
    for ch, n in sorted((man.get("chapters") or {}).items(), key=lambda x: -x[1]):
        print(f"  {ch}: {n}")


if __name__ == "__main__":
    asyncio.run(main())
