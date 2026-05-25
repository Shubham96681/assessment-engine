"""
Clean tangent–secant givens — PQ must divide PA² for integer PR when using PQ² = PR × PT.
"""
from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

_TANGENT_LEN_RE = re.compile(
    r"\btangent\s+([A-Z])([A-Z])\s*=\s*(\d+(?:\.\d+)?)\s*cm",
    re.I,
)
_SECANT_NEAR_RE = re.compile(
    r"\bsecant\s+[A-Z]+\s+meets.*?at\s+[A-Z]\s+\(nearer.*?\)\s+and\s+[A-Z]\s+with\s+"
    r"([A-Z])([A-Z])\s*=\s*(\d+(?:\.\d+)?)\s*cm",
    re.I,
)


def _divisors(n: int) -> List[int]:
    if n <= 0:
        return []
    out: List[int] = []
    for d in range(1, int(math.isqrt(n)) + 1):
        if n % d == 0:
            out.append(d)
            q = n // d
            if q != d:
                out.append(q)
    return sorted(out)


def pick_clean_pq(pa: int, *, prefer: Optional[int] = None) -> int:
    """Choose PQ so PA²/PQ is integer and PT = PR+PQ is reasonable for secant."""
    divs = [d for d in _divisors(pa * pa) if 3 <= d <= min(pa, 25)]
    if not divs:
        return max(3, pa // 3)
    if prefer and prefer in divs:
        return prefer
    # Prefer divisors that yield moderate PR (4–20) with typical PR given in stem
    for pq in sorted(divs, key=lambda x: (abs(x - 9), x)):
        pr = (pa * pa) // pq
        if 4 <= pr <= 30:
            return pq
    return divs[len(divs) // 2]


def parse_tangent_secant_lengths(stem: str) -> Optional[Tuple[str, str, float, str, str, float]]:
    """Return (ext, contact, pa_len, sec_from, sec_to, pr_len) when detectable."""
    if not stem:
        return None
    tm = _TANGENT_LEN_RE.search(stem)
    sm = _SECANT_NEAR_RE.search(stem)
    if not tm or not sm:
        return None
    ext, contact, pa = tm.group(1).upper(), tm.group(2).upper(), float(tm.group(3))
    s_from, s_to, pr = sm.group(1).upper(), sm.group(2).upper(), float(sm.group(3))
    return ext, contact, pa, s_from, s_to, pr


def tangent_secant_pr_is_clean(pa: float, pq: float) -> bool:
    if pa <= 0 or pq <= 0:
        return True
    pr = (pa * pa) / pq
    return abs(pr - round(pr)) < 1e-6


def repair_tangent_secant_stem(stem: str) -> Tuple[str, bool]:
    """
    Replace messy tangent/secant lengths so PA² = PR × PT yields integer PT.
    Fixes PQ (tangent) when present; otherwise adjusts PR (nearer secant segment).
    """
    parsed = parse_tangent_secant_lengths(stem)
    if not parsed:
        return stem, False
    ext, contact, pa_f, s_from, s_to, pr_f = parsed
    pa = int(round(pa_f))
    pr = int(round(pr_f))
    pa_sq = pa * pa

    tm = _TANGENT_LEN_RE.search(stem)
    if not tm:
        return stem, False
    tan_label = f"{tm.group(1).upper()}{tm.group(2).upper()}"

    # Tangent length explicitly given (often mislabeled PQ in RAG output)
    tan_m = re.search(
        rf"\b{re.escape(tan_label)}\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        stem,
        re.I,
    )
    if tan_m:
        tan_len = float(tan_m.group(1))
        if not tangent_secant_pr_is_clean(tan_len, pr):
            # Pick PR so tan_len² / PR is integer
            divs = [d for d in _divisors(int(round(tan_len * tan_len))) if 4 <= d <= 25]
            preferred = [9, 5, 15, 25, 20, 12, 10, 8, 6, 4]
            new_pr = next((d for d in preferred if d in divs and d != pr), None)
            if new_pr is None:
                new_pr = next((d for d in divs if d != pr), pick_clean_pq(int(round(tan_len))))
            new_stem, n = re.subn(
                rf"(\b{re.escape(s_from)}{re.escape(s_to)}\s*=\s*)\d+(?:\.\d+)?(\s*cm)",
                rf"\g<1>{new_pr}\2",
                stem,
                count=1,
                flags=re.I,
            )
            return (new_stem if n else stem), bool(n)

    return stem, False
