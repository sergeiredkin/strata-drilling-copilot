"""Resample to a uniform grid without filling, and turn holes into gap intervals —
docs/07_DATA_AND_ALGORITHMS.md §3.5: "Resample to 1 s grid without filling; holes > 5 s become
gap(`no_data`)." A hole of 5 s or less stays a null on the grid (rendered as a small visual gap by
the front end) but is not reported as a named `no_data` interval — only genuinely missing spans are
counted against QC's gap-hours/score."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class GapInterval:
    t0: datetime
    t1: datetime
    reason: str


def resample_to_grid(
    t: list[datetime], values: list[float], grid_seconds: float
) -> tuple[list[datetime], list[float | None]]:
    """Builds a uniform grid spanning [min(t), max(t)] at `grid_seconds` resolution, assigning
    each original sample to its nearest grid point (snap, never interpolate). Empty if `t` is
    empty."""
    if not t:
        return [], []
    t0 = t[0]
    step = timedelta(seconds=grid_seconds)
    n_steps = int(round((t[-1] - t0).total_seconds() / grid_seconds)) + 1
    grid_t = [t0 + step * i for i in range(n_steps)]
    grid_v: list[float | None] = [None] * n_steps
    for ti, vi in zip(t, values, strict=True):
        idx = int(round((ti - t0).total_seconds() / grid_seconds))
        if 0 <= idx < n_steps:
            grid_v[idx] = vi
    return grid_t, grid_v


def find_no_data_gaps(grid_t: list[datetime], grid_v: list[float | None], gap_seconds: float) -> list[GapInterval]:
    """Maximal runs of null grid points whose span exceeds `gap_seconds` become a `no_data`
    gap interval (t0 = start of the run, t1 = end of the run)."""
    gaps: list[GapInterval] = []
    n = len(grid_v)
    i = 0
    while i < n:
        if grid_v[i] is not None:
            i += 1
            continue
        run_start = i
        while i < n and grid_v[i] is None:
            i += 1
        run_end = i - 1
        span = (grid_t[run_end] - grid_t[run_start]).total_seconds()
        if span > gap_seconds:
            gaps.append(GapInterval(t0=grid_t[run_start], t1=grid_t[run_end], reason="no_data"))
    return gaps
