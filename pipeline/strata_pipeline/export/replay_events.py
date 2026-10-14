"""T13.1 replay event export — docs/06_SCREENS.md S8: state transitions + alerts
(`slow_connection`, `unreported_reaming`, `flat_time`, `data_gap`) for `wells/{id}/replay_events.json`.
Sample events are NOT included here — docs/03_ARCHITECTURE.md §3.1: StaticSource's replay streams
samples straight from the already-exported L0 series chunks, merging them with this file's state/
alert events by timestamp; duplicating the raw samples into a second file would be both wasteful
and a second source of truth for the same numbers.

Alert rules, as named in 06 S8 (not more precisely specified there, so each threshold below is
the simplest literal reading of that one sentence — recorded here rather than re-derived):
- `data_gap`: every R0 ("core channel in gap") rig-state interval, the same rule QC/rig-state
  already computes elsewhere — not a second gap-detection pass.
- `flat_time`: a single contiguous circulating/idle interval longer than 15 min.
- `unreported_reaming`: a reaming interval that overlaps a DDR row coded DRILL (not REAM) at
  all — same condition `kpi/ilt/flat_and_reaming.py:ilt_reaming` sums, but emitted per-interval
  here instead of summed.
- `slow_connection`: a connection whose `conn_s2s` duration exceeds 1.5x the well-level composite
  best for `conn_s2s` (`kpi_report["cards"]`) — well-level, not per-section, since section
  derivation (`sections.json`) isn't built yet for real wells (ADR-worthy if this needs
  revisiting once it is).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kpi.connections import ConnectionKPI
from ..kpi.ilt.overlap import overlap_seconds
from ..rigstate.intervals import RigStateInterval

FLAT_TIME_THRESHOLD_S = 15 * 60
SLOW_CONNECTION_FACTOR = 1.5
_FLAT_STATES = {"circulating"}


def _to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _state_events(intervals: list[RigStateInterval]) -> list[dict[str, Any]]:
    return [{"type": "state", "t": _to_ms(iv.t0), "state": iv.state} for iv in intervals]


def _data_gap_alerts(intervals: list[RigStateInterval]) -> list[dict[str, Any]]:
    gaps = [iv for iv in intervals if iv.rule_id == "R0"]
    return [
        {
            "type": "alert",
            "t": _to_ms(iv.t0),
            "alert": {
                "id": f"alert_gap_{i}",
                "kind": "data_gap",
                "message": f"Core channel gap, {(iv.t1 - iv.t0).total_seconds() / 60:.0f} min",
            },
        }
        for i, iv in enumerate(gaps)
    ]


def _flat_time_alerts(intervals: list[RigStateInterval]) -> list[dict[str, Any]]:
    out = []
    i = 0
    for iv in intervals:
        is_flat = iv.state in _FLAT_STATES or (iv.state == "unknown" and iv.rule_id != "R0")
        duration_s = (iv.t1 - iv.t0).total_seconds()
        if is_flat and duration_s > FLAT_TIME_THRESHOLD_S:
            out.append(
                {
                    "type": "alert",
                    "t": _to_ms(iv.t0),
                    "alert": {
                        "id": f"alert_flat_{i}",
                        "kind": "flat_time",
                        "message": f"Flat time {duration_s / 60:.0f} min ({iv.state})",
                    },
                }
            )
            i += 1
    return out


def _unreported_reaming_alerts(
    intervals: list[RigStateInterval], ddr_rows_raw: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    drill_windows = [(r["t0"], r["t1"]) for r in ddr_rows_raw if r["normalized_code"] == "DRILL"]
    out = []
    i = 0
    for iv in intervals:
        if iv.state != "reaming":
            continue
        if any(overlap_seconds(iv.t0, iv.t1, t0, t1) > 0 for t0, t1 in drill_windows):
            out.append(
                {
                    "type": "alert",
                    "t": _to_ms(iv.t0),
                    "alert": {
                        "id": f"alert_reaming_{i}",
                        "kind": "unreported_reaming",
                        "message": "Reaming during a DDR row coded DRILL, not REAM",
                    },
                }
            )
            i += 1
    return out


def _slow_connection_alerts(
    connections: list[ConnectionKPI], kpi_report: dict[str, Any]
) -> list[dict[str, Any]]:
    card = next((c for c in kpi_report["cards"] if c["kpi"] == "conn_s2s"), None)
    best = card["best"]["value"] if card and card.get("best") else None
    if best is None or best <= 0:
        return []
    threshold_s = best * 60.0 * SLOW_CONNECTION_FACTOR  # best is in minutes (07 §5's conn_s2s unit)
    out = []
    i = 0
    for conn in connections:
        if conn.conn_s2s_seconds > threshold_s:
            out.append(
                {
                    "type": "alert",
                    "t": _to_ms(conn.t0),
                    "alert": {
                        "id": f"alert_slowconn_{i}",
                        "kind": "slow_connection",
                        "message": (
                            f"Connection took {conn.conn_s2s_seconds / 60:.1f} min, "
                            f"> 1.5x composite best ({best:.1f} min)"
                        ),
                    },
                }
            )
            i += 1
    return out


def build_replay_events(
    intervals: list[RigStateInterval],
    ddr_rows_raw: list[dict[str, Any]],
    connections: list[ConnectionKPI],
    kpi_report: dict[str, Any],
) -> list[dict[str, Any]]:
    """Every event in `t` order — S2's replay reducer expects a single time-ordered stream to
    merge with the L0 sample stream, not events grouped by type."""
    events = (
        _state_events(intervals)
        + _data_gap_alerts(intervals)
        + _flat_time_alerts(intervals)
        + _unreported_reaming_alerts(intervals, ddr_rows_raw)
        + _slow_connection_alerts(connections, kpi_report)
    )
    events.sort(key=lambda e: e["t"])
    return events


__all__ = ["FLAT_TIME_THRESHOLD_S", "SLOW_CONNECTION_FACTOR", "build_replay_events"]
