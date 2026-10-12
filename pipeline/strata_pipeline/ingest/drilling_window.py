"""Bounds real-time log ingest to a well's actual drilling-activity window(s) — found necessary
against real data (T3.7 smoke test): several Volve wellbores carry 2-3 *years* of real-time WITSML
history (recurring interventions/sidetracks on the same long-lived platform well, not one short
campaign), ballooning per-sample QC/rig-state processing to ~10GB RAM and 10+ minutes for a well
whose actually-relevant data is a small fraction of that span. docs/DATA_INVENTORY.md flagged this
exact need: "the real drilling window per well is narrower and will be derived ... from rig-state
activity, not assumed from the full file date range" — derived here from DDR activity instead,
which is far cheaper to load than the full real-time log and gives the same answer: a DDR row
coded DRILL/CIRC/TRIP/REAM/CASING/CEMENT/BOP means real drilling-phase work was happening in that
window.

Checked against real DDR gap structure (15/9-F-12): gaps between consecutive drilling-coded rows
are either small (<220 h — weekends, weather, normal within-campaign breaks) or enormous
(2564 h / ~107 days; 74871 h / ~8.5 years — genuine separate campaigns). A 500 h merge threshold
cleanly separates the two with wide margin on this well; used as the default everywhere."""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl

_DRILLING_CODES = {"DRILL", "CIRC", "TRIP", "REAM", "CASING", "CEMENT", "BOP"}


def drilling_windows_from_ddr(
    ddr_df: pl.DataFrame, merge_gap_hours: float = 500.0
) -> list[tuple[datetime, datetime]]:
    """Merged [t0, t1] windows covering every DDR row coded as drilling-phase activity, with
    consecutive windows closer than `merge_gap_hours` apart folded into one. Empty if `ddr_df`
    has no drilling-coded rows at all — callers must treat that as "no bound available", not as
    "nothing is in the window"."""
    drilling = ddr_df.filter(pl.col("normalized_code").is_in(list(_DRILLING_CODES))).sort("t0")
    if drilling.is_empty():
        return []

    rows = drilling.select(["t0", "t1"]).to_dicts()
    merge_gap = timedelta(hours=merge_gap_hours)
    merged: list[tuple[datetime, datetime]] = [(rows[0]["t0"], rows[0]["t1"])]
    for row in rows[1:]:
        last_t0, last_t1 = merged[-1]
        if row["t0"] - last_t1 <= merge_gap:
            merged[-1] = (last_t0, max(last_t1, row["t1"]))
        else:
            merged.append((row["t0"], row["t1"]))
    return merged


def in_any_window(t: datetime, windows: list[tuple[datetime, datetime]]) -> bool:
    return any(t0 <= t <= t1 for t0, t1 in windows)
