"""ILT_total — docs/07_DATA_AND_ALGORITHMS.md §6: "ILT_total = sum of the four" categories, with
`excluded_gap_hours` summed across all of them. `booked_npt` (DDR rows with `npt = true`) is
reported next to ILT for the "booked as NPT in DDR" comparison, not part of the ILT sum itself."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .connections import ConnectionIltResult
from .flat_and_reaming import FlatReamingIltResult
from .trips import TripIltResult


@dataclass(frozen=True)
class IltTotal:
    connections_hours: float
    trips_hours: float
    flat_hours: float
    reaming_hours: float
    total_hours: float
    excluded_gap_hours: float


def combine_ilt(
    connections: ConnectionIltResult,
    trips: TripIltResult,
    flat: FlatReamingIltResult,
    reaming: FlatReamingIltResult,
) -> IltTotal:
    connections_h = connections.total_seconds / 3600.0
    trips_h = trips.total_seconds / 3600.0
    flat_h = flat.total_seconds / 3600.0
    reaming_h = reaming.total_seconds / 3600.0
    excluded_h = (
        connections.excluded_gap_seconds
        + trips.excluded_gap_seconds
        + flat.excluded_gap_seconds
        + reaming.excluded_gap_seconds
    ) / 3600.0
    return IltTotal(
        connections_hours=connections_h,
        trips_hours=trips_h,
        flat_hours=flat_h,
        reaming_hours=reaming_h,
        total_hours=connections_h + trips_h + flat_h + reaming_h,
        excluded_gap_hours=excluded_h,
    )


def booked_npt_hours(ddr_rows: list[tuple[datetime, datetime, bool]]) -> float:
    """`ddr_rows` = `(t0, t1, npt_flag)` triples from ddr.parquet."""
    return sum((t1 - t0).total_seconds() for t0, t1, npt in ddr_rows if npt) / 3600.0
