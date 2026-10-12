"""ILT_connections — docs/07_DATA_AND_ALGORITHMS.md §6:
`ILT_connections = Σ_conn max(0, d_conn − best_conn(section))`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from strata_pipeline.kpi.connections import ConnectionKPI

from .overlap import any_overlap, total_overlap_seconds


@dataclass(frozen=True)
class ConnectionIltResult:
    total_seconds: float
    excluded_gap_seconds: float
    n_included: int
    n_excluded_by_gap: int


def ilt_connections(
    connections: list[ConnectionKPI],
    section_by_connection: list[str],
    best_conn_seconds_by_section: dict[str, float],
    gap_intervals: list[tuple[datetime, datetime]],
) -> ConnectionIltResult:
    """`section_by_connection[i]` is the hole section for `connections[i]` (same length/order).
    `best_conn_seconds_by_section` comes from `kpi.composite_best` (P10 of conn_s2s durations)."""
    total = 0.0
    excluded = 0.0
    n_included = 0
    n_excluded = 0
    for conn, section in zip(connections, section_by_connection, strict=True):
        if any_overlap(conn.t0, conn.t1, gap_intervals):
            excluded += total_overlap_seconds(conn.t0, conn.t1, gap_intervals)
            n_excluded += 1
            continue
        best = best_conn_seconds_by_section.get(section)
        if best is None:
            continue
        total += max(0.0, conn.conn_s2s_seconds - best)
        n_included += 1
    return ConnectionIltResult(
        total_seconds=total, excluded_gap_seconds=excluded, n_included=n_included, n_excluded_by_gap=n_excluded
    )
