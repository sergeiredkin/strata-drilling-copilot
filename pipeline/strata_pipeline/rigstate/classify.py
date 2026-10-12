"""Rig-state top-level orchestration — docs/07_DATA_AND_ALGORITHMS.md §4. Runs pre-processing,
per-sample rule classification, trip-direction smoothing, and interval building/merging/confidence
over a well's core channels, already on a common 1 s grid (QC's output)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .calibration import compute_hl_slips
from .flags import compute_flags
from .intervals import RigStateInterval, build_intervals
from .preprocess import block_velocity, hold_last_value, median_filter
from .rules import CORE_CHANNELS, RuleResult, classify_sample


@dataclass(frozen=True)
class RigStateRun:
    intervals: list[RigStateInterval]
    hl_slips: float
    hl_slips_method: str


def _trip_directions(bitdepth: list[float | None], window_samples: int) -> list[str | None]:
    n = len(bitdepth)
    out: list[str | None] = [None] * n
    for i in range(n):
        lo = max(0, i - window_samples)
        a, b = bitdepth[lo], bitdepth[i]
        if a is None or b is None:
            continue
        net = b - a
        if net > 0:
            out[i] = "trip_in"
        elif net < 0:
            out[i] = "trip_out"
    return out


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
    v = block_velocity(filtered["BPOS"], cfg["block_velocity_window_seconds"], grid_seconds)

    slips = compute_hl_slips(filtered["HKLD"], travelling_block_weight, cfg["slips_fallback_margin"])

    window_samples = max(1, round(cfg["trip_direction_window_seconds"] / grid_seconds))
    trip_dirs = _trip_directions(filtered["BITDEPTH"], window_samples)

    results: list[RuleResult] = []
    for i in range(len(t)):
        raw = {c: filtered[c][i] for c in CORE_CHANNELS}
        flags = compute_flags(
            hkld=raw["HKLD"],
            bitdepth=raw["BITDEPTH"],
            holedepth=raw["HOLEDEPTH"],
            rpm=raw["RPM"],
            flowin=raw["FLOWIN"],
            v=v[i],
            hl_slips=slips.hl_slips,
            cfg=cfg,
        )
        results.append(classify_sample(raw, flags, trip_dirs[i], slips.hl_slips, cfg))

    intervals = build_intervals(t, results, cfg["min_interval_seconds"], cfg["confidence_margin_frac"])
    return RigStateRun(intervals=intervals, hl_slips=slips.hl_slips, hl_slips_method=slips.method)
