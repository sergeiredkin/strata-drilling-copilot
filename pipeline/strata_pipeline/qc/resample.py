"""Resample to a uniform grid without filling, and turn holes into gap intervals —
docs/07_DATA_AND_ALGORITHMS.md §3.5: "Resample to 1 s grid without filling; holes > 5 s become
gap(`no_data`)." A hole of 5 s or less stays a null on the grid (rendered as a small visual gap by
the front end) but is not reported as a named `no_data` interval — only genuinely missing spans are
counted against QC's gap-hours/score."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np


@dataclass(frozen=True)
class GapInterval:
    t0: datetime
    t1: datetime
    reason: str


def resample_to_grid(
    t: list[datetime], values: list[float], grid_seconds: float
) -> tuple[datetime | None, np.ndarray]:
    """Builds a uniform grid spanning [min(t), max(t)] at `grid_seconds` resolution, assigning
    each original sample to its nearest grid point (snap, never interpolate). Returns the grid's
    first timestamp (`None` if `t` is empty) and a dense `float64` array (`NaN` = gap) — not the
    full list of grid timestamps, since every grid point is just `t0 + i * grid_seconds`:
    materializing that as a `list[datetime]` per channel is pure duplication once a well has
    several channels sharing the same grid. The value array itself is `float32`/`NaN` rather than
    `list[float | None]` for the same reason at the next level down: a multi-year-gap real well
    (e.g. drilling campaigns separated by months of workover history) can resample to tens of
    millions of grid points per channel, where a `list[float | None]` of that length costs far
    more than a numpy array of the same length (found via instrumented profiling of
    15/9-F-1_C, whose outer span is ~21x its actual drilling-active time). `float32` (not `64`)
    because this grid is held for every channel simultaneously in `run_well_qc`, and drilling
    sensor data has nowhere near 52 bits of real precision — the STRS export format
    (`export/series.py`) already stores everything as `f32` for the same reason."""
    if not t:
        return None, np.array([], dtype=np.float32)
    t0 = t[0]
    n_steps = int(round((t[-1] - t0).total_seconds() / grid_seconds)) + 1
    grid_v = np.full(n_steps, np.nan, dtype=np.float32)
    offsets = np.array([(ti - t0).total_seconds() for ti in t], dtype=np.float64)
    idx = np.round(offsets / grid_seconds).astype(np.int64)
    values_arr = np.asarray(values, dtype=np.float32)
    valid = (idx >= 0) & (idx < n_steps)
    # Repeated indices (two raw samples snapping to the same grid point) resolve to the last one
    # in input order, same as the original per-sample loop — numpy's plain fancy-index
    # assignment applies repeated indices in array order, so this is not a behavior change.
    grid_v[idx[valid]] = values_arr[valid]
    return t0, grid_v


def find_no_data_gaps(
    t0: datetime | None, grid_v: np.ndarray, grid_seconds: float, gap_seconds: float
) -> list[GapInterval]:
    """Maximal runs of null grid points whose span exceeds `gap_seconds` become a `no_data`
    gap interval (t0 = start of the run, t1 = end of the run). `t0`/`grid_seconds` describe the
    grid arithmetically (see `resample_to_grid`) instead of a materialized timestamp list. Run
    boundaries are found with one vectorized diff over the whole array rather than a per-sample
    Python loop (same reasoning as qc/frozen.py's run detection — real wells make `grid_v` tens
    of millions of elements long)."""
    if t0 is None or len(grid_v) == 0:
        return []
    isnan = np.isnan(grid_v)
    if not isnan.any():
        return []
    step = timedelta(seconds=grid_seconds)
    padded = np.concatenate(([False], isnan, [False]))
    edges = np.diff(padded.astype(np.int8))
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0] - 1

    gaps: list[GapInterval] = []
    for run_start, run_end in zip(starts.tolist(), ends.tolist(), strict=True):
        span = (run_end - run_start) * grid_seconds
        if span > gap_seconds:
            gaps.append(GapInterval(t0=t0 + step * run_start, t1=t0 + step * run_end, reason="no_data"))
    return gaps
