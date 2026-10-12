"""Rig-state pre-processing — docs/07_DATA_AND_ALGORITHMS.md §4: "5 s median filter on inputs;
block velocity v = dBPOS/dt (5 s centred)." Operates on a value already resampled to a uniform
1 s grid (QC's job); nulls pass through untouched so a gap stays a gap, never gets smoothed over.
"""

from __future__ import annotations


def median_filter(values: list[float | None], window_seconds: float, grid_seconds: float = 1.0) -> list[float | None]:
    """Centred rolling median with a `window_seconds`-wide window (converted to samples via
    `grid_seconds`). A null stays null; it is excluded from neighbouring windows' medians."""
    half = max(1, round(window_seconds / grid_seconds / 2))
    n = len(values)
    out: list[float | None] = [None] * n
    for i in range(n):
        if values[i] is None:
            continue
        lo, hi = max(0, i - half), min(n, i + half + 1)
        window = [v for v in values[lo:hi] if v is not None]
        out[i] = _median(window) if window else None
    return out


def block_velocity(bpos: list[float | None], window_seconds: float, grid_seconds: float = 1.0) -> list[float | None]:
    """v[i] = (bpos[i + half] - bpos[i - half]) / (2 * half * grid_seconds), a centred difference
    over `window_seconds`. Null wherever either endpoint is missing."""
    half = max(1, round(window_seconds / grid_seconds / 2))
    n = len(bpos)
    out: list[float | None] = [None] * n
    span = 2 * half * grid_seconds
    for i in range(n):
        lo, hi = i - half, i + half
        if lo < 0 or hi >= n:
            continue
        v_lo, v_hi = bpos[lo], bpos[hi]
        if v_lo is None or v_hi is None:
            continue
        out[i] = (v_hi - v_lo) / span
    return out


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0
