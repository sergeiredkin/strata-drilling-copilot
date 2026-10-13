"""Frozen-value detection — docs/07_DATA_AND_ALGORITHMS.md §3.4: a dynamic channel reading the
same non-zero value for more than 300 s is a stuck sensor, not a real constant state, and must
become a gap(`frozen_value`).

Vectorized (see qc/spikes.py's docstring for why): run boundaries are found with a single
`np.unique` call instead of a per-sample Python loop, and every run's value/validity/span is
checked and scattered back to a per-sample mask in one vectorized pass — no Python-level loop
over either samples or runs, so this stays fast even on a channel that changes almost every
sample (worst case for a naive per-run loop)."""

from __future__ import annotations

from datetime import datetime

import numpy as np

_TOL = 1e-9


def frozen_value_mask(t: list[datetime], values: list[float | None], min_seconds: float) -> list[bool]:
    """True for every sample inside a run of equal, non-zero, non-null values whose time span
    exceeds `min_seconds`. A run's span is measured start-to-end timestamp (not sample count), so
    it still triggers under irregular sampling."""
    n = len(values)
    if n == 0:
        return []

    arr = np.array([np.nan if v is None else v for v in values], dtype=np.float64)
    valid = ~np.isnan(arr)
    t_sec = np.array([ti.timestamp() for ti in t], dtype=np.float64)

    same_as_prev = np.zeros(n, dtype=bool)
    same_as_prev[1:] = valid[1:] & valid[:-1] & (np.abs(arr[1:] - arr[:-1]) < _TOL)
    run_id = np.cumsum(~same_as_prev)  # 1..n_runs, contiguous and monotonically non-decreasing

    _, run_starts = np.unique(run_id, return_index=True)
    run_ends = np.append(run_starts[1:] - 1, n - 1)

    run_values = arr[run_starts]
    run_valid = valid[run_starts]
    run_span = t_sec[run_ends] - t_sec[run_starts]
    frozen_run = run_valid & (np.abs(run_values) > _TOL) & (run_span > min_seconds)

    mask = frozen_run[run_id - 1]
    result: list[bool] = mask.tolist()
    return result
