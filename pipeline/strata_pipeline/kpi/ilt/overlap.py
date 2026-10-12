"""Shared interval-overlap helpers for ILT — docs/07_DATA_AND_ALGORITHMS.md §6: "intervals
overlapping a gap are excluded and summed in excluded_gap_hours." An ILT-contributing interval
(a connection, a trip, a flat/reaming stretch) that touches an R0 `unknown` gap at all is dropped
from its category's sum entirely — we can't trust its duration/distance when part of its input
data was missing — and the actual overlapped seconds (not the whole interval) are added to
excluded_gap_hours, so that count reflects real missing-data time, not padded by valid time next
to it."""

from __future__ import annotations

from datetime import datetime


def overlap_seconds(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> float:
    lo = max(a0, b0)
    hi = min(a1, b1)
    return max(0.0, (hi - lo).total_seconds())


def any_overlap(a0: datetime, a1: datetime, intervals: list[tuple[datetime, datetime]]) -> bool:
    return any(overlap_seconds(a0, a1, b0, b1) > 0 for b0, b1 in intervals)


def total_overlap_seconds(a0: datetime, a1: datetime, intervals: list[tuple[datetime, datetime]]) -> float:
    return sum(overlap_seconds(a0, a1, b0, b1) for b0, b1 in intervals)
