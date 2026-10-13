"""Builds the per-well static-export JSON payloads (`04_DATA_CONTRACTS.md` §3) from the real
pipeline modules built in T2.2-T3.6 — the real-data counterpart of `fixtures/kpi.py`, which does
the same job over `fixtures/synth.py`'s synthesized ground truth. One hole section ("unknown") is
used throughout: `sections.parquet` derivation (casing/hole-size records) isn't built yet
(docs/DATA_INVENTORY.md), so composite-best always falls back to well level — which is already
the correct, documented behaviour of `kpi.composite_best` when a section has too few samples, not
a special case this module needs to add.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from strata_pipeline.confidence import assess
from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.kpi.composite_best import Kind, compute_composite_best
from strata_pipeline.kpi.connections import ConnectionKPI, compute_connections, expand_states
from strata_pipeline.kpi.distributions import Sample, compute_distribution
from strata_pipeline.kpi.flat_time import flat_time_pct as calc_flat_time_pct
from strata_pipeline.kpi.flat_time import on_bottom_pct as calc_on_bottom_pct
from strata_pipeline.kpi.ilt.connections import ilt_connections
from strata_pipeline.kpi.ilt.flat_and_reaming import ilt_flat, ilt_reaming
from strata_pipeline.kpi.ilt.report import booked_npt_hours, combine_ilt
from strata_pipeline.kpi.ilt.trips import ilt_trips
from strata_pipeline.kpi.trips import TripSegment, compute_trips
from strata_pipeline.recon.reconciliation import DdrRow, compute_reconciliation
from strata_pipeline.rigstate.intervals import RigStateInterval

SECTION = "unknown"  # placeholder hole section — see module docstring


def _to_none_list(arr: np.ndarray) -> list[float | None]:
    """`arr` is float64 with `NaN` = gap (see qc.align.align_well_channels) — JSON export needs
    `null`, not a literal `NaN` token (not valid JSON)."""
    return [None if np.isnan(v) else float(v) for v in arr]


def build_depthtime_json(
    t: list[datetime], channels: dict[str, np.ndarray], stride_s: int = 60
) -> dict[str, Any]:
    idx = range(0, len(t), stride_s)
    hole = channels.get("HOLEDEPTH")
    bit = channels.get("BITDEPTH")
    # Slice to the stride FIRST (a numpy view, no copy), then convert — this only materializes
    # ~1/stride_s of the channel as Python objects instead of the full per-second array (which
    # can be tens of millions of samples on a multi-year-gap real well).
    hole_strided = _to_none_list(hole[::stride_s]) if hole is not None else [None] * len(idx)
    bit_strided = _to_none_list(bit[::stride_s]) if bit is not None else [None] * len(idx)
    return {
        "t": [int(t[i].timestamp() * 1000) for i in idx],
        "bit_md": bit_strided,
        "hole_md": hole_strided,
    }


def build_sections_json() -> list[dict[str, Any]]:
    """Empty: `sections.parquet` derivation (casing/hole-size records, or the DDR-narrative +
    bit-size-change fallback) isn't built yet (docs/DATA_INVENTORY.md) — an honest empty list,
    not a guessed single section, since the front end's section-based views should show
    "no section data" rather than one fabricated boundary."""
    return []


def build_rigstate_json(intervals: list[RigStateInterval]) -> list[dict[str, Any]]:
    return [
        {
            "t0": int(iv.t0.timestamp() * 1000),
            "t1": int(iv.t1.timestamp() * 1000),
            "state": iv.state,
            "p": iv.confidence,
            "rule_id": iv.rule_id,
        }
        for iv in intervals
    ]


def build_ddr_json(well: str, ddr_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`ddr_rows` are the raw dicts from `ingest.ddr.load_well_ddr` (one per `<activity>`).
    `npt` defaults to `False` for every row: Volve's WITSML DDR activities carry no explicit NPT
    boolean (`ingest/ddr.py`'s `npt_flag` is `None` for the same reason), and the contract's
    `DdrRow.npt` field is non-nullable — defaulting False never claims a row IS NPT, it only
    means "no booked-NPT source found", which is what T2.2/T2.3 actually confirmed."""
    return [
        {
            "id": f"ddr_{well}_{i}",
            "t0": int(row["t0"].timestamp() * 1000),
            "t1": int(row["t1"].timestamp() * 1000),
            "code": row["normalized_code"],
            "raw_code": row["raw_code"],
            "md_from": row["md"],
            "md_to": row["md"],
            "narrative": row["narrative"],
            "report_date": row["report_date"],
            "npt": bool(row.get("npt_flag")),
        }
        for i, row in enumerate(ddr_rows)
    ]


def gap_intervals_from_rigstate(intervals: list[RigStateInterval]) -> list[tuple[datetime, datetime]]:
    return [(iv.t0, iv.t1) for iv in intervals if iv.rule_id == "R0"]


def _kpi_dist_card(
    name: str,
    values: list[float],
    windows: list[tuple[int, int]],
    unit: str,
    kind: Kind,
    tool: str,
    well: str,
    reg: EvidenceRegistry,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Returns (card, distribution|None) in the `KpiReport.cards`/`distributions` shape."""
    source = [{"file": "pipeline:real", "sha256": "n/a"}]
    conf = assess(sample_size=len(values))
    if not values:
        eid = reg.add(tool, {"well": well, "stat": "value"}, None, unit, source)
        null_card = {
            "kpi": name,
            "value": {"value": None, "unit": unit, "evidence_id": eid},
            "best": None,
            "confidence": conf,
        }
        return null_card, None

    dist = compute_distribution([Sample(value=v, window=w) for v, w in zip(values, windows, strict=True)])
    assert dist is not None
    best_result = compute_composite_best(values, values, kind)

    def q(stat: str, value: float) -> dict[str, Any]:
        return reg.quantity(tool, {"well": well, "stat": stat}, value, unit, source, 2)

    dist_payload = {
        "n": dist.n,
        "min": q("min", dist.min),
        "q1": q("q1", dist.q1),
        "median": q("median", dist.median),
        "q3": q("q3", dist.q3),
        "max": q("max", dist.max),
        "composite_best": q("composite_best", best_result.value) if best_result.value is not None else None,
        "outliers": [
            {"value": q("outlier", o.value), "t0": o.window[0], "t1": o.window[1]} for o in dist.outliers
        ],
    }
    best_q = dist_payload["composite_best"]
    card = {"kpi": name, "value": q("median", dist.median), "best": best_q, "confidence": conf}
    return card, {"kpi": name, "section": SECTION, "dist": dist_payload}


def build_kpis(
    well: str,
    t: list[datetime],
    channels: dict[str, np.ndarray],
    intervals: list[RigStateInterval],
    reg: EvidenceRegistry,
) -> tuple[dict[str, Any], list[ConnectionKPI], list[TripSegment]]:
    states = expand_states(intervals, t)
    wob = channels.get("WOB")
    bitdepth = channels.get("BITDEPTH")
    connections = compute_connections(
        t, _to_none_list(wob) if wob is not None else [None] * len(t), states, intervals
    )
    trips = compute_trips(
        t, _to_none_list(bitdepth) if bitdepth is not None else [None] * len(t), intervals, casing_shoe_md=None
    )

    conn_s2s = [c.conn_s2s_seconds / 60.0 for c in connections]
    conn_windows = [(int(c.t0.timestamp() * 1000), int(c.t1.timestamp() * 1000)) for c in connections]
    conn_w2w = [c.conn_w2w_seconds / 60.0 for c in connections if c.conn_w2w_seconds is not None]
    conn_w2w_windows = [
        (int(c.t0.timestamp() * 1000), int(c.t1.timestamp() * 1000))
        for c in connections
        if c.conn_w2w_seconds is not None
    ]

    trip_in = [tr for tr in trips if tr.direction == "trip_in"]
    trip_out = [tr for tr in trips if tr.direction == "trip_out"]
    trip_in_speed = [tr.speed_m_per_h for tr in trip_in]
    trip_out_speed = [tr.speed_m_per_h for tr in trip_out]
    trip_in_windows = [(int(tr.t0.timestamp() * 1000), int(tr.t1.timestamp() * 1000)) for tr in trip_in]
    trip_out_windows = [(int(tr.t0.timestamp() * 1000), int(tr.t1.timestamp() * 1000)) for tr in trip_out]

    cards = []
    distributions = []
    duration_defs: list[tuple[str, list[float], list[tuple[int, int]], str]] = [
        ("conn_s2s", conn_s2s, conn_windows, "min"),
        ("conn_w2w", conn_w2w, conn_w2w_windows, "min"),
    ]
    speed_defs: list[tuple[str, list[float], list[tuple[int, int]], str]] = [
        ("trip_in_open", trip_in_speed, trip_in_windows, "m/h"),
        ("trip_out_open", trip_out_speed, trip_out_windows, "m/h"),
    ]
    for name, values, windows, unit in duration_defs:
        card, dist = _kpi_dist_card(name, values, windows, unit, "duration", "kpi.connection_times", well, reg)
        cards.append(card)
        if dist is not None:
            distributions.append(dist)
    for name, values, windows, unit in speed_defs:
        card, dist = _kpi_dist_card(name, values, windows, unit, "speed", "kpi.trips", well, reg)
        cards.append(card)
        if dist is not None:
            distributions.append(dist)

    for name in ("trip_in_cased", "trip_out_cased"):
        eid = reg.add("kpi.trips", {"well": well, "stat": name}, None, "m/h", [])
        cards.append(
            {
                "kpi": name,
                "value": {"value": None, "unit": "m/h", "evidence_id": eid},
                "best": None,
                "confidence": assess(sample_size=0),
            }
        )

    flat_frac = calc_flat_time_pct(intervals)
    on_bottom_frac = calc_on_bottom_pct(intervals)
    flat_pct = flat_frac * 100.0 if flat_frac is not None else None
    on_bottom = on_bottom_frac * 100.0 if on_bottom_frac is not None else None
    source = [{"file": "pipeline:real", "sha256": "n/a"}]
    cards.append(
        {
            "kpi": "flat_time_pct",
            "value": reg.quantity("kpi.flat_time", {"well": well}, flat_pct, "%", source, 1),
            "best": None,
            "confidence": assess(sample_size=1 if flat_pct is not None else 0),
        }
    )
    cards.append(
        {
            "kpi": "on_bottom_pct",
            "value": reg.quantity("kpi.on_bottom", {"well": well}, on_bottom, "%", source, 1),
            "best": None,
            "confidence": assess(sample_size=1 if on_bottom is not None else 0),
        }
    )

    overall_conf = assess(sample_size=len(connections) + len(trips))
    report = {"well": well, "cards": cards, "distributions": distributions, "confidence": overall_conf}
    return report, connections, trips


def build_ilt(
    well: str,
    kpi_report: dict[str, Any],
    connections: list[ConnectionKPI],
    trips: list[TripSegment],
    intervals: list[RigStateInterval],
    ddr_rows_raw: list[dict[str, Any]],
    reg: EvidenceRegistry,
) -> dict[str, Any]:
    def best(kpi_name: str) -> float | None:
        card = next((c for c in kpi_report["cards"] if c["kpi"] == kpi_name), None)
        return card["best"]["value"] if card and card["best"] else None

    best_conn = best("conn_s2s")
    best_trip_speed = best("trip_in_open")
    gaps = gap_intervals_from_rigstate(intervals)

    conn_result = ilt_connections(
        connections,
        [SECTION] * len(connections),
        {SECTION: best_conn * 60.0} if best_conn is not None else {},
        gaps,
    )
    trip_result = ilt_trips(
        trips,
        [SECTION] * len(trips),
        {(SECTION, "open"): best_trip_speed} if best_trip_speed else {},
        gaps,
    )

    ddr_tuples = [(r["t0"], r["t1"], r["normalized_code"]) for r in ddr_rows_raw]
    drill_trip_rows = [t for t in ddr_tuples if t[2] in ("DRILL", "TRIP")]
    drill_rows = [t for t in ddr_tuples if t[2] == "DRILL"]
    flat_result = ilt_flat(intervals, drill_trip_rows, gaps)
    reaming_result = ilt_reaming(intervals, drill_rows, gaps)

    total = combine_ilt(conn_result, trip_result, flat_result, reaming_result)
    source = [{"file": "pipeline:real", "sha256": "n/a"}]

    def q(value: float, params: dict[str, Any]) -> dict[str, Any]:
        return reg.quantity("kpi.ilt_breakdown", {"well": well, **params}, value, "h", source, 2)

    categories = {
        "connections": total.connections_hours,
        "trips": total.trips_hours,
        "flat_time": total.flat_hours,
        "unreported_reaming": total.reaming_hours,
    }
    by_category = [{"category": cat, "hours": q(hours, {"category": cat})} for cat, hours in categories.items()]
    by_section = [
        {
            "section": SECTION,
            "by_category": {cat: q(hours, {"section": SECTION, "category": cat}) for cat, hours in categories.items()},
            "total": q(total.total_hours, {"section": SECTION, "stat": "total"}),
        }
    ]
    # See build_ddr_json's docstring: no real NPT source in Volve's DDR activities yet, so this
    # is always 0 rather than a guess — booked_npt_hours sums only rows where npt_flag is True.
    npt_rows = [(r["t0"], r["t1"], bool(r.get("npt_flag"))) for r in ddr_rows_raw]

    return {
        "well": well,
        "definition": {
            "text": "ILT = connection + trip overrun vs. composite-best, plus unreported flat/reaming time.",
            "baseline": "composite_best",
            "percentile": 10.0,
        },
        "total": q(total.total_hours, {"stat": "total"}),
        "booked_npt": q(booked_npt_hours(npt_rows), {"stat": "booked_npt"}),
        "by_category": by_category,
        "by_section": by_section,
        "by_day": [],
        "excluded_gap_hours": q(total.excluded_gap_hours, {"stat": "excluded_gap_hours"}),
    }


def build_reconciliation(
    well: str,
    ddr_rows_raw: list[dict[str, Any]],
    intervals: list[RigStateInterval],
    cfg: dict[str, Any],
    reg: EvidenceRegistry,
) -> dict[str, Any]:
    ddr_rows = [DdrRow(t0=r["t0"], t1=r["t1"], normalized_code=r["normalized_code"]) for r in ddr_rows_raw]
    result = compute_reconciliation(
        ddr_rows, intervals, cfg["expected_states"], cfg["included_codes"], cfg["boundary_slack_min"]
    )
    source = [{"file": "pipeline:real", "sha256": "n/a"}]

    def q(value: float, params: dict[str, Any], unit: str = "min") -> dict[str, Any]:
        return reg.quantity("recon.cell", {"well": well, **params}, value, unit, source, 2)

    def cell(code: str, state: str) -> dict[str, Any]:
        c = result.cells[code][state]
        return {"minutes": q(c.minutes, {"code": code, "state": state}), "pct": c.pct}

    cells = [[cell(code, state) for state in result.cols] for code in result.rows]
    def agreement_pct_q(code: str, pct: float | None) -> dict[str, Any]:
        if pct is None:
            eid = reg.add("recon.agreement", {"well": well, "code": code}, None, "%", source)
            return {"value": None, "unit": "%", "evidence_id": eid}
        return reg.quantity("recon.agreement", {"well": well, "code": code}, pct, "%", source, 1)

    def booked_q(code: str, booked_minutes: float) -> dict[str, Any]:
        return reg.quantity("recon.booked", {"well": well, "code": code}, booked_minutes / 60.0, "h", source, 2)

    agreement = [
        {"code": a.code, "pct": agreement_pct_q(a.code, a.pct), "booked": booked_q(a.code, a.booked_minutes)}
        for a in result.agreement
    ]
    per_well_q = (
        reg.quantity("recon.per_well", {"well": well}, result.per_well_agreement, "%", source, 1)
        if result.per_well_agreement is not None
        else {"value": None, "unit": "%", "evidence_id": reg.add("recon.per_well", {"well": well}, None, "%", source)}
    )
    return {
        "scope": well,
        "rows": list(result.rows),
        "cols": list(result.cols),
        "cells": cells,
        "agreement": agreement,
        "per_well": [{"well": well, "agreement": per_well_q}],
        "tolerance": {"boundary_slack_min": cfg["boundary_slack_min"], "min_duration_min": cfg["min_duration_min"]},
    }
