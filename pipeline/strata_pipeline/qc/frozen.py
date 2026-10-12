"""Frozen-value detection — docs/07_DATA_AND_ALGORITHMS.md §3.4: a dynamic channel reading the
same non-zero value for more than 300 s is a stuck sensor, not a real constant state, and must
become a gap(`frozen_value`)."""

from __future__ import annotations

from datetime import datetime

_TOL = 1e-9


def frozen_value_mask(t: list[datetime], values: list[float | None], min_seconds: float) -> list[bool]:
    """True for every sample inside a run of equal, non-zero, non-null values whose time span
    exceeds `min_seconds`. A run's span is measured start-to-end timestamp (not sample count), so
    it still triggers under irregular sampling."""
    n = len(values)
    mask = [False] * n
    run_start = 0
    i = 1
    while i <= n:
        v_i = values[i] if i < n else None
        v_start = values[run_start]
        same_as_start = i < n and v_i is not None and v_start is not None and abs(v_i - v_start) < _TOL
        if same_as_start:
            i += 1
            continue
        run_end = i - 1
        v = values[run_start]
        if v is not None and abs(v) > _TOL:
            span = (t[run_end] - t[run_start]).total_seconds()
            if span > min_seconds:
                for j in range(run_start, run_end + 1):
                    mask[j] = True
        run_start = i
        i += 1
    return mask
