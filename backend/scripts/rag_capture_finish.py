#!/usr/bin/env python3
"""Validate rag_response.txt and finish the pending assessment (no UI click)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.generation.rag_capture import (  # noqa: E402
    is_rag_response_ready_for_apply,
    read_capture_signal,
)


def main() -> int:
    ok, reason = is_rag_response_ready_for_apply()
    if not ok:
        print(f"NOT READY: {reason}", file=sys.stderr)
        return 1
    sig = read_capture_signal()
    aid = sig.get("assessment_id")
    if not aid:
        print("No assessment_id — click Generate in the UI first.", file=sys.stderr)
        return 1
    base = settings.API_INTERNAL_BASE_URL.rstrip("/")
    url = f"{base}/api/v1/rag/finish-capture"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"HTTP {e.code}: {body[:500]}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Backend not reachable at {base}: {e}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "assessment_id": data.get("assessment_id") or aid,
                "status": data.get("status"),
                "questions": data.get("questions"),
                "total_marks": data.get("total_marks"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
