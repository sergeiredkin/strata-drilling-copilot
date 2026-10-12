"""KPI / ILT / reconciliation computation over a synthesized `WellDetail`.

Formulas: `07_DATA_AND_ALGORITHMS.md` §5-7. This is the fixture-era implementation referenced by
T1.2 ("KPIs/ILT computed ... by synth.py with identical formulas" until the real Phase-3 pipeline
exists) — the real pipeline (T3.3/T3.4/T3.5) will run the same formulas over real rig-state
output instead of a synthesized ground truth.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from ..confidence import assess
from ..evidence import EvidenceRegistry
from .synth import DAY_S, WellDetail

# DDR code -> expected sensor states (07_DATA_AND_ALGORITHMS.md §7). Codes mapping to an empty
# set are excluded from reconciliation agreement entirely.
CODE_EXPECTED: dict[str, set[str]] = {
    "DRILL": {"rotary_drilling", "sliding", "connection"},
    "CIRC": {"circulating"},
    "TRIP": {"trip_in", "trip_out"},
    "REAM": {"reaming", "circulating"},
}

_SOURCE = [{"file": "fixtures/synth.py", "sha256": "mock-fixture", "channels": ["HKLD", "BPOS", "WOB"]}]


def _pctl(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype="f8"), q)) if values else 0.0


def _minutes(t0_ms: float, t1_ms: float) -> float:
    return (t1_ms - t0_ms) / 60_000.0


def _day_key(t_ms: float, t0_ms: float) -> str:
    base = datetime(2015, 6, 1)
    day_idx = int((t_ms - t0_ms) // (DAY_S * 1000))
    return (base + timedelta(days=day_idx)).date().isoformat()


def compute_kpis(detail: WellDetail, reg: EvidenceRegistry) -> dict[str, Any]:
    well = detail.spec.id
    section = detail.spec.sections[-1] if detail.spec.sections else "unknown"

    conn = [s for s in detail.state_intervals if s[2] == "connection"]
    conn_s2s = [_minutes(s[0], s[1]) for s in conn]
    conn_w2w = [d * 1.15 for d in conn_s2s]  # simplification: no separate WOB-based boundary

    trip_in = [s for s in detail.state_intervals if s[2] == "trip_in"]
    trip_out = [s for s in detail.state_intervals if s[2] == "trip_out"]
    trip_in_speed = [
        detail.md_start / max(_minutes(s[0], s[1]) / 60.0, 1e-6) for s in trip_in
    ]  # m/h, open hole (no casing shoe tracked in fixtures)
    trip_out_speed = [
        detail.md_start / max(_minutes(s[0], s[1]) / 60.0, 1e-6) for s in trip_out
    ]

    valid_states = [s for s in detail.state_intervals if not (s[2] == "unknown" and s[3] == 0.0)]
    total_valid_min = sum(_minutes(s[0], s[1]) for s in valid_states) or 1.0
    flat_min = sum(_minutes(s[0], s[1]) for s in valid_states if s[2] in ("circulating", "reaming"))
    on_bottom_min = sum(
        _minutes(s[0], s[1]) for s in valid_states if s[2] in ("rotary_drilling", "sliding")
    )

    def dist(
        values: list[float], windows: list[tuple[float, float]], tool: str, unit: str, better: str
    ) -> dict[str, Any] | None:
        if not values:
            return None
        best_pctl = 10.0 if better == "low" else 90.0
        best = _pctl(values, best_pctl)
        outliers: list[tuple[float, float, float]] = []
        if len(values) >= 4:
            q1, q3 = _pctl(values, 25), _pctl(values, 75)
            iqr = q3 - q1
            hi = q3 + 1.5 * iqr
            outliers = [(v, w[0], w[1]) for v, w in zip(values, windows) if v > hi]
        return {
            "n": len(values),
            "min": reg.quantity(tool, {"well": well, "stat": "min"}, min(values), unit, _SOURCE, 2),
            "q1": reg.quantity(tool, {"well": well, "stat": "q1"}, _pctl(values, 25), unit, _SOURCE, 2),
            "median": reg.quantity(tool, {"well": well, "stat": "median"}, _pctl(values, 50), unit, _SOURCE, 2),
            "q3": reg.quantity(tool, {"well": well, "stat": "q3"}, _pctl(values, 75), unit, _SOURCE, 2),
            "max": reg.quantity(tool, {"well": well, "stat": "max"}, max(values), unit, _SOURCE, 2),
            "composite_best": reg.quantity(
                tool, {"well": well, "stat": f"p{best_pctl:.0f}"}, best, unit, _SOURCE, 2,
                method_note=f"composite best = P{best_pctl:.0f} per KPI per section",
            ),
            "outliers": [
                {
                    "value": reg.quantity(tool, {"well": well, "stat": "outlier"}, v, unit, _SOURCE, 2),
                    "t0": t0,
                    "t1": t1,
                }
                for v, t0, t1 in outliers
            ],
        }

    conn_windows = [(s[0], s[1]) for s in conn]
    trip_in_windows = [(s[0], s[1]) for s in trip_in]
    trip_out_windows = [(s[0], s[1]) for s in trip_out]

    cards = []
    distributions = []
    kpi_defs = [
        ("conn_s2s", conn_s2s, conn_windows, "min", "low", "kpi.connection_times"),
        ("conn_w2w", conn_w2w, conn_windows, "min", "low", "kpi.connection_times"),
        ("trip_in_open", trip_in_speed, trip_in_windows, "m/h", "high", "kpi.trips"),
        ("trip_out_open", trip_out_speed, trip_out_windows, "m/h", "high", "kpi.trips"),
    ]
    for name, values, windows, unit, better, tool in kpi_defs:
        d = dist(values, windows, tool, unit, better)
        conf = assess(sample_size=len(values)) if values else assess(sample_size=0)
        if d is None:
            eid = reg.add(tool, {"well": well, "stat": "value"}, None, unit, _SOURCE)
            null_value = {"value": None, "unit": unit, "evidence_id": eid}
            cards.append({"kpi": name, "value": null_value, "best": None, "confidence": conf})
        else:
            cards.append({"kpi": name, "value": d["median"], "best": d["composite_best"], "confidence": conf})
            distributions.append({"kpi": name, "section": section, "dist": d})

    for name in ("trip_in_cased", "trip_out_cased"):
        eid = reg.add("kpi.trips", {"well": well, "stat": name}, None, "m/h", _SOURCE)
        cards.append({
            "kpi": name,
            "value": {"value": None, "unit": "m/h", "evidence_id": eid},
            "best": None,
            "confidence": assess(sample_size=0),
        })

    flat_pct = flat_min / total_valid_min * 100
    on_bottom_pct = on_bottom_min / total_valid_min * 100
    cards.append({
        "kpi": "flat_time_pct",
        "value": reg.quantity("kpi.flat_time", {"well": well}, flat_pct, "%", _SOURCE, 1),
        "best": None,
        "confidence": assess(sample_size=len(valid_states)),
    })
    cards.append({
        "kpi": "on_bottom_pct",
        "value": reg.quantity("kpi.on_bottom", {"well": well}, on_bottom_pct, "%", _SOURCE, 1),
        "best": None,
        "confidence": assess(sample_size=len(valid_states)),
    })

    overall_conf = assess(sample_size=len(conn_s2s) + len(trip_in) + len(trip_out))
    return {"well": well, "cards": cards, "distributions": distributions, "confidence": overall_conf}


def compute_ilt(
    detail: WellDetail, reg: EvidenceRegistry, kpi_report: dict[str, Any]
) -> dict[str, Any]:
    well = detail.spec.id
    section = detail.spec.sections[-1] if detail.spec.sections else "unknown"

    def _best(kpi_name: str) -> float | None:
        return next(
            (c["best"]["value"] for c in kpi_report["cards"] if c["kpi"] == kpi_name and c["best"]), None
        )

    best_conn = _best("conn_s2s")
    best_trip_speed = _best("trip_in_open")

    contributions: list[tuple[str, str, float]] = []  # (category, day_key, minutes)

    for s in detail.state_intervals:
        if s[2] != "connection" or best_conn is None:
            continue
        d = _minutes(s[0], s[1])
        over = max(0.0, d - best_conn)
        if over > 0:
            contributions.append(("connections", _day_key(s[0], detail.t0_ms), over))

    for s in detail.state_intervals:
        if s[2] not in ("trip_in", "trip_out") or best_trip_speed is None:
            continue
        d_h = _minutes(s[0], s[1]) / 60.0
        best_h = detail.md_start / best_trip_speed if best_trip_speed else d_h
        over_min = max(0.0, (d_h - best_h) * 60.0)
        if over_min > 0:
            contributions.append(("trips", _day_key(s[0], detail.t0_ms), over_min))

    drill_rows = [(r[0], r[1]) for r in detail.ddr_rows if r[2] == "DRILL"]
    trip_rows = [(r[0], r[1]) for r in detail.ddr_rows if r[2] == "TRIP"]

    def overlap_minutes(state_name: str, rows: list[tuple[float, float]]) -> list[tuple[str, float]]:
        out = []
        for s in detail.state_intervals:
            if s[2] != state_name:
                continue
            for r0, r1 in rows:
                ov0, ov1 = max(s[0], r0), min(s[1], r1)
                if ov1 > ov0:
                    out.append((_day_key(ov0, detail.t0_ms), _minutes(ov0, ov1)))
        return out

    for day_key, minutes in overlap_minutes("circulating", drill_rows + trip_rows):
        contributions.append(("flat_time", day_key, minutes))
    for day_key, minutes in overlap_minutes("reaming", drill_rows):
        contributions.append(("unreported_reaming", day_key, minutes))

    by_category_min: dict[str, float] = {}
    by_day_min: dict[str, float] = {}
    for cat, day_key, minutes in contributions:
        by_category_min[cat] = by_category_min.get(cat, 0.0) + minutes
        by_day_min[day_key] = by_day_min.get(day_key, 0.0) + minutes

    total_min = sum(by_category_min.values())

    def q_hours(minutes: float, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        return reg.quantity(tool, params, minutes / 60.0, "h", _SOURCE, 2)

    categories = ("connections", "trips", "flat_time", "unreported_reaming")
    by_category = [
        {
            "category": cat,
            "hours": q_hours(by_category_min.get(cat, 0.0), "kpi.ilt_breakdown", {"well": well, "category": cat}),
        }
        for cat in categories
    ]
    section_params = {"well": well, "section": section}
    by_section = [{
        "section": section,
        "by_category": {
            cat: q_hours(by_category_min.get(cat, 0.0), "kpi.ilt_breakdown", {**section_params, "category": cat})
            for cat in categories
        },
        "total": q_hours(total_min, "kpi.ilt_breakdown", {**section_params, "stat": "total"}),
    }]

    gap_minutes = sum(_minutes(s[0], s[1]) for s in detail.state_intervals if s[2] == "unknown" and s[3] == 0.0)
    by_day = []
    for day_idx in range(detail.spec.dense_days):
        day_key = _day_key(detail.t0_ms + day_idx * DAY_S * 1000, detail.t0_ms)
        coverage_pct = max(0.0, 1.0 - (gap_minutes / detail.spec.dense_days) / (DAY_S / 60.0)) * 100
        by_day.append({
            "date": day_key,
            "hours": q_hours(by_day_min.get(day_key, 0.0), "kpi.ilt_breakdown", {"well": well, "day": day_key}),
            "coverage_pct": round(coverage_pct, 1),
        })

    booked_npt_min = sum(_minutes(r[0], r[1]) for r in detail.ddr_rows if r[5])

    return {
        "well": well,
        "definition": {
            "text": (
                "Invisible lost time is the excess of each connection/trip over the composite "
                "best (P10 of durations, or P90 of speeds) for its section, plus circulating or "
                "reaming time inside DDR rows coded DRILL/TRIP that the report does not call out."
            ),
            "baseline": "composite_best",
            "percentile": 10,
        },
        "total": q_hours(total_min, "kpi.ilt_breakdown", {"well": well, "stat": "total"}),
        "booked_npt": q_hours(booked_npt_min, "kpi.ilt_breakdown", {"well": well, "stat": "booked_npt"}),
        "by_category": by_category,
        "by_section": by_section,
        "by_day": by_day,
        "excluded_gap_hours": q_hours(0.0, "kpi.ilt_breakdown", {"well": well, "stat": "excluded_gap_hours"}),
    }


def compute_mismatches(detail: WellDetail, reg: EvidenceRegistry) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    boundary_slack_ms = 5 * 60 * 1000
    min_run_ms = 2 * 60 * 1000

    for i, row in enumerate(detail.ddr_rows):
        t0, t1, code = row[0], row[1], row[2]
        expected = CODE_EXPECTED.get(code)
        if not expected:
            continue
        core_t0, core_t1 = t0 + boundary_slack_ms, t1 - boundary_slack_ms
        if core_t1 <= core_t0:
            continue

        run_start: float | None = None
        run_state: str | None = None

        def flush(end: float, row_i: int = i, row_code: str = code, row_t0: float = t0, row_t1: float = t1) -> None:
            nonlocal run_start, run_state
            if run_start is not None and run_state is not None and end - run_start >= min_run_ms:
                dur_min = (end - run_start) / 60_000.0
                mismatches.append({
                    "id": f"mm_{detail.spec.id}_{row_i}_{len(mismatches)}",
                    "t0": run_start,
                    "t1": end,
                    "sensor_state": run_state,
                    "sensor_p": 0.85,
                    "ddr_code": row_code,
                    "ddr_activity_id": f"ddr_{detail.spec.id}_{row_i}",
                    "overlap_pct": round((end - run_start) / (row_t1 - row_t0) * 100, 1),
                    "duration": reg.quantity(
                        "recon.mismatch", {"well": detail.spec.id, "row": row_i}, dur_min, "min", _SOURCE, 1
                    ),
                    "tolerance": {"boundary_slack_min": 5, "min_duration_min": 2},
                })
            run_start, run_state = None, None

        for s in detail.state_intervals:
            if s[1] <= core_t0 or s[0] >= core_t1:
                continue
            seg_t0 = max(s[0], core_t0)
            outside = s[2] not in expected
            if outside:
                if run_start is None:
                    run_start, run_state = seg_t0, s[2]
                elif run_state != s[2]:
                    flush(seg_t0)
                    run_start, run_state = seg_t0, s[2]
            else:
                flush(seg_t0)
        flush(core_t1)

    return mismatches


ALL_RIG_STATES = [
    "rotary_drilling", "sliding", "connection", "trip_in", "trip_out",
    "reaming", "circulating", "out_of_hole", "unknown",
]


def compute_reconciliation(detail: WellDetail, reg: EvidenceRegistry) -> dict[str, Any]:
    """Minutes of each measured rig state within each DDR code's row windows (minus the
    ±5 min boundary slack), per `07_DATA_AND_ALGORITHMS.md` §7."""
    well = detail.spec.id
    boundary_slack_ms = 5 * 60 * 1000
    codes = sorted({r[2] for r in detail.ddr_rows})
    minutes_by: dict[str, dict[str, float]] = {code: dict.fromkeys(ALL_RIG_STATES, 0.0) for code in codes}
    row_total_min: dict[str, float] = dict.fromkeys(codes, 0.0)

    for t0, t1, code, *_rest in detail.ddr_rows:
        core_t0, core_t1 = t0 + boundary_slack_ms, t1 - boundary_slack_ms
        if core_t1 <= core_t0:
            continue
        row_total_min[code] += (core_t1 - core_t0) / 60_000.0
        for s in detail.state_intervals:
            ov0, ov1 = max(s[0], core_t0), min(s[1], core_t1)
            if ov1 > ov0:
                minutes_by[code][s[2]] += (ov1 - ov0) / 60_000.0

    def cell_minutes(code: str, state: str) -> dict[str, Any]:
        return reg.quantity(
            "recon.matrix", {"well": well, "code": code, "state": state}, minutes_by[code][state], "min", _SOURCE, 1
        )

    cells = [
        [
            {
                "minutes": cell_minutes(code, state),
                "pct": round(minutes_by[code][state] / row_total_min[code] * 100, 1) if row_total_min[code] else 0.0,
            }
            for state in ALL_RIG_STATES
        ]
        for code in codes
    ]

    agreement: list[dict[str, Any]] = []
    for code in codes:
        expected = CODE_EXPECTED.get(code)
        if not expected or row_total_min[code] == 0:
            continue
        agree_min = sum(minutes_by[code][s] for s in expected)
        agree_pct = agree_min / row_total_min[code] * 100
        pct_q = reg.quantity("recon.agreement", {"well": well, "code": code}, agree_pct, "%", _SOURCE, 1)
        agreement.append({"code": code, "pct": pct_q})

    weighted_total = sum(row_total_min[a["code"]] for a in agreement)
    well_agreement_pct = (
        sum(a["pct"]["value"] * row_total_min[a["code"]] for a in agreement) / weighted_total
        if weighted_total
        else None
    )
    per_well = []
    if well_agreement_pct is not None:
        overall_q = reg.quantity(
            "recon.agreement", {"well": well, "stat": "overall"}, well_agreement_pct, "%", _SOURCE, 1
        )
        per_well.append({"well": well, "agreement": overall_q})

    return {
        "scope": well,
        "rows": codes,
        "cols": ALL_RIG_STATES,
        "cells": cells,
        "agreement": agreement,
        "per_well": per_well,
        "tolerance": {"boundary_slack_min": 5, "min_duration_min": 2},
    }
