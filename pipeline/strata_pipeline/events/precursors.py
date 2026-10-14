"""T12.2 precursor windows — docs/07_DATA_AND_ALGORITHMS.md §10: "6 h before event start for
HKLD, TORQ, SPP (+ pick-up weights from trip connections); normal band = P10-P90 of the same
channel in rotary_drilling/trip windows within ±50 m MD in the same well and offsets. No risk
score is computed or shown."

Scope note: the "+ pick-up weights from trip connections" channel and the "...and offsets" half
of the normal-band population are NOT built here. Pick-up weight is a derived KPI
(`kpi/connections.py`), not a raw channel, and wiring it in is its own small module; cross-well
("offset") banding needs more than one well with real dense channel data in the same band
(today: one real well, see tasks/BACKLOG.md T3.7) to mean anything beyond "this well's own
history," so the band computed here is explicitly same-well-only, labelled as such in
`baseline_note` rather than silently presented as the full cross-well band the spec describes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from ..kpi.connections import expand_states
from ..rigstate.intervals import RigStateInterval

PRECURSOR_CHANNELS: tuple[str, ...] = ("HKLD", "TORQ", "SPP")
_UNITS = {"HKLD": "kN", "TORQ": "kN.m", "SPP": "bar"}
WINDOW_HOURS = 6.0
MD_TOLERANCE_M = 50.0
_NORMAL_STATES = frozenset({"rotary_drilling", "trip_in", "trip_out"})
_TARGET_POINTS = 360  # a 6h sparkline (S6's aside, ~300px wide) never needs 1Hz resolution


def build_precursors(
    issue: dict[str, Any],
    t: list[datetime],
    channels: dict[str, np.ndarray],
    intervals: list[RigStateInterval],
) -> dict[str, Any] | None:
    """`None` when there isn't enough to build anything honest from: no time series at all, or
    the issue has no MD (the band lookup needs it) — never a guessed window or band."""
    if not t or issue.get("md") is None:
        return None

    t_ms = np.array([ti.timestamp() * 1000.0 for ti in t])
    window_start_ms = issue["t0"] - WINDOW_HOURS * 3_600_000.0
    in_window_full = (t_ms >= window_start_ms) & (t_ms <= issue["t0"])
    if not np.any(in_window_full):
        return None
    # Downsample the exported window (not the band computation below, which uses every sample)
    # to ~_TARGET_POINTS -- a sparkline doesn't need 1Hz resolution, and at 1Hz a 6h window is
    # 21,600 points per channel otherwise.
    full_indices = np.where(in_window_full)[0]
    stride = max(1, round(len(full_indices) / _TARGET_POINTS))
    window_indices = full_indices[::stride]

    md = float(issue["md"])
    bitdepth = channels.get("BITDEPTH")
    near_md = np.abs(bitdepth - md) <= MD_TOLERANCE_M if bitdepth is not None else np.zeros(len(t), dtype=bool)
    states = expand_states(intervals, t)
    in_normal_state = np.array([s in _NORMAL_STATES for s in states])
    band_mask = near_md & in_normal_state

    channel_entries = []
    for name in PRECURSOR_CHANNELS:
        arr = channels.get(name)
        if arr is None:
            continue
        band_values = arr[band_mask & np.isfinite(arr)]
        lo, hi = (
            (float(np.percentile(band_values, 10)), float(np.percentile(band_values, 90)))
            if band_values.size >= 2
            else (None, None)
        )
        window_t = t_ms[window_indices]
        window_values = arr[window_indices]
        n = len(window_t)
        channel_entries.append(
            {
                "channel": name,
                "unit": _UNITS[name],
                "t": window_t.tolist(),
                "value": [None if not np.isfinite(v) else float(v) for v in window_values],
                "band_lo": [lo] * n,
                "band_hi": [hi] * n,
            }
        )
    if not channel_entries:
        return None

    return {
        "issue_id": issue["id"],
        "window_h": WINDOW_HOURS,
        "channels": channel_entries,
        "baseline_note": (
            "Band = P10-P90 of the same channel during rotary drilling/tripping within "
            f"{MD_TOLERANCE_M:.0f} m MD, this well only (no offset well with real channel data "
            "yet). Shown for inspection only -- no risk score."
        ),
    }


__all__ = ["MD_TOLERANCE_M", "PRECURSOR_CHANNELS", "WINDOW_HOURS", "build_precursors"]
