"""Spike removal — docs/07_DATA_AND_ALGORITHMS.md §3.3: Hampel filter, window 31 samples,
threshold 6·MAD, single-sample spikes only (a run of consecutive outliers is a real excursion,
not a spike, and must be left alone).

Vectorized with numpy's sliding_window_view: found necessary against real multi-well data (the
T3.7/audit-era smoke tests) — the original pure-Python per-sample loop rebuilt and re-sorted a
window-sized sublist at every one of millions of samples, which was both slow and, worse,
allocated enough short-lived list/tuple garbage to balloon peak RSS into the multi-gigabyte range
on wells with a few million samples. This computes the exact same per-window-local median and MAD
(not a global rolling median referenced against a different window's value), just without the
per-sample Python-level reallocation."""

from __future__ import annotations

import warnings

import numpy as np

_MAD_TO_SIGMA = 1.4826  # scales MAD to be comparable to a Gaussian std-dev
_TOL = 1e-9


def hampel_spike_mask(values: list[float | None], window: int, threshold: float) -> list[bool]:
    """True at index i iff values[i] is an isolated outlier under a centred rolling-median Hampel
    test. Null/NaN samples are never flagged (nothing to remove) and are excluded from each
    window's median/MAD computation. A flagged index that is immediately adjacent to another
    flagged index is un-flagged (per spec: "single samples only")."""
    n = len(values)
    if n == 0:
        return []
    arr = np.array([np.nan if v is None else v for v in values], dtype=np.float64)
    half = window // 2

    padded = np.pad(arr, (half, half), mode="constant", constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)  # shape (n, window)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # all-NaN window is expected
        med = np.nanmedian(windows, axis=1)
        mad = np.nanmedian(np.abs(windows - med[:, None]), axis=1)

    valid = ~np.isnan(arr)
    enough_samples = np.sum(~np.isnan(windows), axis=1) >= 3
    deviation = np.abs(arr - med)

    zero_mad = mad == 0
    # Zero spread in the window: any deviation at all is an outlier (nothing "normal" to compare
    # against). Otherwise, the standard Hampel threshold test.
    flagged = np.where(zero_mad, deviation > _TOL, deviation > threshold * _MAD_TO_SIGMA * mad)
    raw_mask = valid & enough_samples & flagged

    left_flagged = np.zeros(n, dtype=bool)
    left_flagged[1:] = raw_mask[:-1]
    right_flagged = np.zeros(n, dtype=bool)
    right_flagged[:-1] = raw_mask[1:]
    mask = raw_mask & ~(left_flagged | right_flagged)
    result: list[bool] = mask.tolist()
    return result
