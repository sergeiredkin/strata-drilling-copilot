"""QC orchestration — docs/07_DATA_AND_ALGORITHMS.md §3, run in the written order: unit fix →
sentinels → spikes → frozen values → resample-without-fill (holes > 5 s → gap(no_data)) → report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import polars as pl

from .frozen import frozen_value_mask
from .reconcile import pick_source_per_channel
from .resample import GapInterval, find_no_data_gaps, resample_to_grid
from .sentinels import sentinel_mask
from .spikes import hampel_spike_mask
from .units import UnitFixEvent, detect_and_fix_unit


@dataclass
class ChannelQCResult:
    channel: str
    clean_t: list[datetime]
    clean_values: list[float | None]
    gaps: list[GapInterval]
    unit_fix: UnitFixEvent | None
    reason_counts: dict[str, int] = field(default_factory=dict)
    survived_fraction: float = 1.0


def run_channel_qc(t: list[datetime], values: list[float], channel: str, cfg: dict[str, Any]) -> ChannelQCResult:
    n_total = len(values)
    if n_total == 0:
        return ChannelQCResult(channel, [], [], [], None, {}, 1.0)

    fixed_values, unit_fix = detect_and_fix_unit(values, channel, cfg)

    working: list[float | None] = list(fixed_values)
    gaps: list[GapInterval] = []
    reason_counts: dict[str, int] = {}

    sentinel_flagged = sentinel_mask(pl.Series(working, dtype=pl.Float64), cfg["sentinels"]).to_list()
    gaps += _flag(t, working, sentinel_flagged, "sentinel", reason_counts)

    spike_flagged = hampel_spike_mask(working, cfg["spike_hampel_window"], cfg["spike_hampel_threshold_mad"])
    gaps += _flag(t, working, spike_flagged, "removed_spike", reason_counts)

    frozen_flagged = frozen_value_mask(t, working, cfg["frozen_min_seconds"])
    gaps += _flag(t, working, frozen_flagged, "frozen_value", reason_counts)

    kept_t = [ti for ti, vi in zip(t, working, strict=True) if vi is not None]
    kept_v = [vi for vi in working if vi is not None]
    grid_t, grid_v = resample_to_grid(kept_t, kept_v, cfg["resample_grid_seconds"])
    gaps += find_no_data_gaps(grid_t, grid_v, cfg["resample_gap_seconds"])

    n_removed = sum(reason_counts.values())
    survived_fraction = (n_total - n_removed) / n_total if n_total else 1.0

    return ChannelQCResult(channel, grid_t, grid_v, gaps, unit_fix, reason_counts, survived_fraction)


def _flag(
    t: list[datetime],
    working: list[float | None],
    flagged: list[bool],
    reason: str,
    reason_counts: dict[str, int],
) -> list[GapInterval]:
    """Marks flagged samples as removed (sets them to None in `working`) and returns one
    GapInterval per contiguous run of flagged samples, keyed by original sample order."""
    gaps: list[GapInterval] = []
    n = len(working)
    i = 0
    while i < n:
        if not flagged[i]:
            i += 1
            continue
        run_start = i
        while i < n and flagged[i]:
            working[i] = None
            i += 1
        run_end = i - 1
        reason_counts[reason] = reason_counts.get(reason, 0) + (run_end - run_start + 1)
        gaps.append(GapInterval(t0=t[run_start], t1=t[run_end], reason=reason))
    return gaps


def run_well_qc(long_df: pl.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    """Reconciles each channel to its richest source log, runs per-channel QC, and aggregates a
    well-level report matching the EvalReport.qc shape in `contracts/schemas/strata.schema.json`
    (well, gap_hours, spikes_removed, unit_fixes, sentinels_removed) plus per-channel detail."""
    reconciled, source_report = pick_source_per_channel(long_df)
    channels: dict[str, ChannelQCResult] = {}
    for channel in sorted(reconciled["channel"].unique()):
        sub = reconciled.filter(pl.col("channel") == channel).sort("t")
        channels[channel] = run_channel_qc(sub["t"].to_list(), sub["value"].to_list(), channel, cfg)

    total_gap_seconds = 0.0
    spikes_removed = 0
    sentinels_removed = 0
    unit_fixes = 0
    for result in channels.values():
        for gap in result.gaps:
            total_gap_seconds += (gap.t1 - gap.t0).total_seconds()
        spikes_removed += result.reason_counts.get("removed_spike", 0)
        sentinels_removed += result.reason_counts.get("sentinel", 0)
        if result.unit_fix is not None:
            unit_fixes += 1

    return {
        "gap_hours": total_gap_seconds / 3600.0,
        "spikes_removed": spikes_removed,
        "unit_fixes": unit_fixes,
        "sentinels_removed": sentinels_removed,
        "channels": channels,
        "source_report": source_report,
    }
