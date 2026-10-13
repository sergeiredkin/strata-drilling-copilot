"""Rig-state top-level orchestration — docs/07_DATA_AND_ALGORITHMS.md §4. Runs pre-processing,
per-sample rule classification, trip-direction smoothing, and interval building/merging/confidence
over a well's core channels, already on a common 1 s grid (QC's output)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from .calibration import compute_hl_slips
from .intervals import RigStateInterval, build_intervals_from_arrays
from .preprocess import block_velocity, hold_last_value, median_filter
from .rules import CORE_CHANNELS
from .vectorized import classify_samples_vectorized, trip_directions_vectorized


@dataclass(frozen=True)
class RigStateRun:
    intervals: list[RigStateInterval]
    hl_slips: float
    hl_slips_method: str


def _to_array(values: list[float | None]) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=np.float64)


def run_rigstate(
    t: list[datetime],
    channels: dict[str, list[float | None]],
    travelling_block_weight: float,
    cfg: dict[str, Any],
    grid_seconds: float = 1.0,
) -> RigStateRun:
    """`channels` must have every key in CORE_CHANNELS (HKLD, BPOS, FLOWIN, RPM, BITDEPTH,
    HOLEDEPTH), each a list the same length as `t`, already on a uniform `grid_seconds` grid with
    `None` at gaps (QC's output)."""
    held = {c: hold_last_value(channels[c], t, cfg["hold_last_value_seconds"]) for c in CORE_CHANNELS}
    filtered = {
        c: median_filter(held[c], cfg["median_filter_seconds"], grid_seconds)
        for c in CORE_CHANNELS
    }
    v = _to_array(block_velocity(filtered["BPOS"], cfg["block_velocity_window_seconds"], grid_seconds))

    slips = compute_hl_slips(filtered["HKLD"], travelling_block_weight, cfg["slips_fallback_margin"])

    core = {c: _to_array(filtered[c]) for c in CORE_CHANNELS}

    window_samples = max(1, round(cfg["trip_direction_window_seconds"] / grid_seconds))
    trip_dirs = trip_directions_vectorized(core["BITDEPTH"], window_samples)

    states, rule_ids, decisive, back_reaming = classify_samples_vectorized(core, v, trip_dirs, slips.hl_slips, cfg)

    intervals = build_intervals_from_arrays(t, states, rule_ids, decisive, back_reaming, cfg["min_interval_seconds"])
    return RigStateRun(intervals=intervals, hl_slips=slips.hl_slips, hl_slips_method=slips.method)
