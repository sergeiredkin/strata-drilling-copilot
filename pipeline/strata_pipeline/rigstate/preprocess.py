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
gap still reads as missing rather than holding forever.

All three functions below take and return `float64` numpy arrays (`NaN` = gap) end to end,
instead of `list[float | None]`: `run_rigstate` calls these once per core channel, and a
multi-year-gap real well's grid can be tens of millions of samples long, where converting
list<->array at every step (as an earlier version of this module did) cost as much as the
vectorized computation itself was saving."""

from __future__ import annotations

import warnings

import numpy as np


def hold_last_value(arr: np.ndarray, t_sec: np.ndarray, max_hold_seconds: float) -> np.ndarray:
    """Forward-fills each NaN with the most recent non-NaN value, as long as that value is no
    more than `max_hold_seconds` old (per `t_sec`, seconds since epoch); reverts to `NaN` once
    staleness exceeds it."""
    n = len(arr)
    if n == 0:
        return arr
    valid = ~np.isnan(arr)

    idx = np.arange(n)
    last_valid_idx = np.where(valid, idx, -1)
    np.maximum.accumulate(last_valid_idx, out=last_valid_idx)

    has_prev = last_valid_idx >= 0
    safe_idx = np.where(has_prev, last_valid_idx, 0)
    age = np.where(has_prev, t_sec - t_sec[safe_idx], np.inf)
    fill_mask = (~valid) & has_prev & (age <= max_hold_seconds)

    held = arr.copy()
    held[fill_mask] = arr[safe_idx][fill_mask]
    held[(~valid) & (~fill_mask)] = np.nan
    return held


def median_filter(arr: np.ndarray, window_seconds: float, grid_seconds: float = 1.0) -> np.ndarray:
    """Centred rolling median with a `window_seconds`-wide window (converted to samples via
    `grid_seconds`). A NaN stays NaN; it is excluded from neighbouring windows' medians."""
    n = len(arr)
    if n == 0:
        return arr
    half = max(1, round(window_seconds / grid_seconds / 2))

    padded = np.pad(arr, (half, half), mode="constant", constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # all-NaN window is expected
        out = np.nanmedian(windows, axis=1)
    out[np.isnan(arr)] = np.nan  # NaN stays NaN regardless of neighbours (matches input exactly)
    result: np.ndarray = out
    return result


def block_velocity(bpos: np.ndarray, window_seconds: float, grid_seconds: float = 1.0) -> np.ndarray:
    """v[i] = (bpos[i + half] - bpos[i - half]) / (2 * half * grid_seconds), a centred difference
    over `window_seconds`. NaN wherever either endpoint is missing."""
    n = len(bpos)
    half = max(1, round(window_seconds / grid_seconds / 2))
    out = np.full(n, np.nan, dtype=np.float32)
    if n > 2 * half:
        span = 2 * half * grid_seconds
        out[half : n - half] = (bpos[2 * half : n] - bpos[0 : n - 2 * half]) / span
    return out
