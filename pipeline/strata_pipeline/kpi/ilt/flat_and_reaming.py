"""ILT_flat / ILT_reaming — docs/07_DATA_AND_ALGORITHMS.md §6:
`ILT_flat = Σ circulating/idle minutes inside DDR rows coded DRILL or TRIP` (flat time not booked
as such).
`ILT_reaming = Σ reaming minutes inside DDR rows coded DRILL` (unreported reaming)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from strata_pipeline.rigstate.intervals import RigStateInterval

from .overlap import overlap_seconds, total_overlap_seconds

_FLAT_STATES = {"circulating"}


@dataclass(frozen=True)
class FlatReamingIltResult:
    total_seconds: float
    excluded_gap_seconds: float


def _sum_overlap_excluding_gaps(
    intervals: list[RigStateInterval],
    ddr_rows: list[tuple[datetime, datetime, str]],
    ddr_codes: set[str],
    gap_intervals: list[tuple[datetime, datetime]],
) -> FlatReamingIltResult:
    ddr_windows = [(t0, t1) for t0, t1, code in ddr_rows if code in ddr_codes]
    total = 0.0
    excluded = 0.0
    for iv in intervals:
        gap_overlap = total_overlap_seconds(iv.t0, iv.t1, gap_intervals)
        if gap_overlap > 0:
            excluded += gap_overlap
            continue
        for t0, t1 in ddr_windows:
            total += overlap_seconds(iv.t0, iv.t1, t0, t1)
    return FlatReamingIltResult(total_seconds=total, excluded_gap_seconds=excluded)


def ilt_flat(
    intervals: list[RigStateInterval],
    ddr_rows: list[tuple[datetime, datetime, str]],
    gap_intervals: list[tuple[datetime, datetime]],
) -> FlatReamingIltResult:
    """`intervals` = circulating or idle (unknown/R10) rig-state intervals only; `ddr_rows` =
    `(t0, t1, normalized_code)` triples from ddr.parquet."""
    flat_intervals = [
        iv for iv in intervals if iv.state in _FLAT_STATES or (iv.state == "unknown" and iv.rule_id == "R10")
    ]
    return _sum_overlap_excluding_gaps(flat_intervals, ddr_rows, {"DRILL", "TRIP"}, gap_intervals)


def ilt_reaming(
    intervals: list[RigStateInterval],
    ddr_rows: list[tuple[datetime, datetime, str]],
    gap_intervals: list[tuple[datetime, datetime]],
) -> FlatReamingIltResult:
    """`intervals` = reaming rig-state intervals only."""
    reaming_intervals = [iv for iv in intervals if iv.state == "reaming"]
    return _sum_overlap_excluding_gaps(reaming_intervals, ddr_rows, {"DRILL"}, gap_intervals)
