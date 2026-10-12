"""Rig-state pre-processing — docs/07_DATA_AND_ALGORITHMS.md §4: "5 s median filter on inputs;
block velocity v = dBPOS/dt (5 s centred)." Operates on a value already resampled to a uniform
1 s grid (QC's job); nulls pass through untouched so a gap stays a gap, never gets smoothed over.

`hold_last_value` is a separate, rig-state-only concern discovered against real Volve data
(docs/DATA_INVENTORY.md's "sampling cadence is irregular" note undersells it): a wellbore's
drilling channels are each sampled independently every ~1-3 s typically (occasionally tens of
seconds), by *different* WITSML log objects on *different* schedules. After QC's null-preserving
1 s grid, the odds of all six core channels landing a real sample on the exact same second are
near zero even when every channel individually has excellent coverage — classify.py found the
real archive collapsing to a single R0 gap interval for an entire well before this existed. QC's
own channel output must stay null-preserving (the UI's gap-hatching depends on it); this function
only feeds rigstate's "what was the most recently known value" need, bounded so a genuinely long
gap still reads as missing rather than holding forever."""

from __future__ import annotations

from datetime import datetime


def hold_last_value(values: list[float | None], t: list[datetime], max_hold_seconds: float) -> list[float | None]:
    """Forward-fills each null with the most recent non-null value, as long as that value is no
    more than `max_hold_seconds` old; reverts to `None` once staleness exceeds it."""
    held: list[float | None] = list(values)
    last_value: float | None = None
    last_t: datetime | None = None
    for i, v in enumerate(values):
        if v is not None:
            last_value, last_t = v, t[i]
            continue
        if last_value is not None and last_t is not None and (t[i] - last_t).total_seconds() <= max_hold_seconds:
            held[i] = last_value
        else:
            held[i] = None
    return held


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
