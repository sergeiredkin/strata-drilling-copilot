"""Spike removal — docs/07_DATA_AND_ALGORITHMS.md §3.3: Hampel filter, window 31 samples,
threshold 6·MAD, single-sample spikes only (a run of consecutive outliers is a real excursion,
not a spike, and must be left alone)."""

from __future__ import annotations

import math

_MAD_TO_SIGMA = 1.4826  # scales MAD to be comparable to a Gaussian std-dev


def hampel_spike_mask(values: list[float | None], window: int, threshold: float) -> list[bool]:
    """True at index i iff values[i] is an isolated outlier under a centred rolling-median Hampel
    test. Null/NaN samples are never flagged (nothing to remove) and are excluded from each
    window's median/MAD computation. A flagged index that is immediately adjacent to another
    flagged index is un-flagged (per spec: "single samples only")."""
    n = len(values)
    half = window // 2
    raw_mask = [False] * n
    for i in range(n):
        v = values[i]
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        lo, hi = max(0, i - half), min(n, i + half + 1)
        window_vals = [x for x in values[lo:hi] if x is not None and not (isinstance(x, float) and math.isnan(x))]
        if len(window_vals) < 3:
            continue
        med = _median(window_vals)
        mad = _median([abs(x - med) for x in window_vals])
        if mad == 0:
            # The window is otherwise constant, so any deviation at all is an outlier (there is
            # no "normal" spread to compare against).
            if abs(v - med) > 1e-9:
                raw_mask[i] = True
            continue
        if abs(v - med) > threshold * _MAD_TO_SIGMA * mad:
            raw_mask[i] = True

    mask = list(raw_mask)
    for i in range(n):
        if raw_mask[i]:
            left_flagged = i > 0 and raw_mask[i - 1]
            right_flagged = i < n - 1 and raw_mask[i + 1]
            if left_flagged or right_flagged:
                mask[i] = False
    return mask


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0
