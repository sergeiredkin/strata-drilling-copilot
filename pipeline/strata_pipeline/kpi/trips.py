"""Trip speed — docs/07_DATA_AND_ALGORITHMS.md §5: "trips = maximal blocks of trip_in/trip_out
allowing in-slips gaps ≤ 10 min; speed = |ΔBITDEPTH| / elapsed h, split into cased/open by the
casing shoe." Per-stand speed distributions are deferred — detecting individual stand cycles
needs a stand-length signal this module doesn't have yet; only whole-trip-block speed is computed
here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from strata_pipeline.rigstate.intervals import RigStateInterval

_TRIP_STATES = {"trip_in", "trip_out"}


@dataclass(frozen=True)
class TripSegment:
    t0: datetime
    t1: datetime
    direction: str  # "trip_in" | "trip_out"
    bitdepth_start: float
    bitdepth_end: float
    speed_m_per_h: float
    section: str  # "cased" | "open" | "mixed"


def compute_trips(
    t: list[datetime],
    bitdepth: list[float | None],
    intervals: list[RigStateInterval],
    casing_shoe_md: float | None,
    max_slips_gap_minutes: float = 10.0,
) -> list[TripSegment]:
    index_by_t = {ti: i for i, ti in enumerate(t)}
    blocks = _group_trip_blocks(intervals, max_slips_gap_minutes * 60.0)

    out: list[TripSegment] = []
    for block in blocks:
        i0 = index_by_t.get(block[0].t0)
        i1 = index_by_t.get(block[-1].t1)
        if i0 is None or i1 is None:
            continue
        d0, d1 = bitdepth[i0], bitdepth[i1]
        if d0 is None or d1 is None:
            continue
        elapsed_h = (block[-1].t1 - block[0].t0).total_seconds() / 3600.0
        if elapsed_h <= 0:
            continue
        direction = next(iv.state for iv in block if iv.state in _TRIP_STATES)
        out.append(
            TripSegment(
                t0=block[0].t0,
                t1=block[-1].t1,
                direction=direction,
                bitdepth_start=d0,
                bitdepth_end=d1,
                speed_m_per_h=abs(d1 - d0) / elapsed_h,
                section=_classify_section(d0, d1, casing_shoe_md),
            )
        )
    return out


def _classify_section(d0: float, d1: float, casing_shoe_md: float | None) -> str:
    if casing_shoe_md is None:
        return "open"
    lo, hi = min(d0, d1), max(d0, d1)
    if hi <= casing_shoe_md:
        return "cased"
    if lo >= casing_shoe_md:
        return "open"
    return "mixed"


def _group_trip_blocks(
    intervals: list[RigStateInterval], max_gap_seconds: float
) -> list[list[RigStateInterval]]:
    """Maximal runs of same-direction trip_in/trip_out intervals, allowing an in-between
    `connection` interval of at most `max_gap_seconds` to be absorbed without breaking the run."""
    blocks: list[list[RigStateInterval]] = []
    current: list[RigStateInterval] = []
    current_direction: str | None = None
    pending_connection: RigStateInterval | None = None

    for iv in intervals:
        if iv.state in _TRIP_STATES:
            if current and iv.state != current_direction:
                blocks.append(current)
                current = []
            if pending_connection is not None:
                if current and iv.state == current_direction:
                    current.append(pending_connection)
                pending_connection = None
            current.append(iv)
            current_direction = iv.state
        elif iv.state == "connection" and current:
            duration = (iv.t1 - iv.t0).total_seconds()
            if duration <= max_gap_seconds:
                pending_connection = iv
            else:
                blocks.append(current)
                current = []
                current_direction = None
                pending_connection = None
        else:
            if current:
                blocks.append(current)
            current = []
            current_direction = None
            pending_connection = None

    if current:
        blocks.append(current)
    return blocks
