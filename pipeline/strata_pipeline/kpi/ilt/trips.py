"""ILT_trips — docs/07_DATA_AND_ALGORITHMS.md §6:
`ILT_trips = Σ_trip max(0, t_trip − distance_trip / best_speed(section, cased|open))`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from strata_pipeline.kpi.trips import TripSegment

from .overlap import any_overlap, total_overlap_seconds


@dataclass(frozen=True)
class TripIltResult:
    total_seconds: float
    excluded_gap_seconds: float
    n_included: int
    n_excluded_by_gap: int


def ilt_trips(
    trips: list[TripSegment],
    section_by_trip: list[str],
    best_speed_m_per_h_by_section: dict[tuple[str, str], float],
    gap_intervals: list[tuple[datetime, datetime]],
) -> TripIltResult:
    """`best_speed_m_per_h_by_section` is keyed `(section, "cased"|"open")` (from
    `kpi.composite_best`, P90 of trip speeds). A trip classified `"mixed"` by
    `kpi.trips._classify_section` has no single best-speed lookup and is skipped — splitting a
    mixed trip's distance across cased/open sub-spans isn't implemented."""
    total = 0.0
    excluded = 0.0
    n_included = 0
    n_excluded = 0
    for trip, section in zip(trips, section_by_trip, strict=True):
        if any_overlap(trip.t0, trip.t1, gap_intervals):
            excluded += total_overlap_seconds(trip.t0, trip.t1, gap_intervals)
            n_excluded += 1
            continue
        if trip.section == "mixed":
            continue
        best_speed = best_speed_m_per_h_by_section.get((section, trip.section))
        if not best_speed:
            continue
        t_trip_h = (trip.t1 - trip.t0).total_seconds() / 3600.0
        distance = abs(trip.bitdepth_end - trip.bitdepth_start)
        ideal_h = distance / best_speed
        total += max(0.0, t_trip_h - ideal_h) * 3600.0
        n_included += 1
    return TripIltResult(
        total_seconds=total, excluded_gap_seconds=excluded, n_included=n_included, n_excluded_by_gap=n_excluded
    )
