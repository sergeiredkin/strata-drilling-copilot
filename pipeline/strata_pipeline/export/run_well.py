"""Top-level per-well orchestration — `make pipeline WELL=<id>`: ingest -> qc -> align ->
rigstate -> kpi/ilt/recon -> write the static-export files for one well
(docs/04_DATA_CONTRACTS.md §3). `run_well_from_dataframes` is the pure, testable core; `run_well`
resolves real on-disk paths and is what the CLI entry point calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import yaml

from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.export.real_well import (
    build_ddr_json,
    build_depthtime_json,
    build_ilt,
    build_kpis,
    build_reconciliation,
    build_rigstate_json,
    build_sections_json,
)
from strata_pipeline.export.series import export_channel_series
from strata_pipeline.ingest.ddr import load_well_ddr
from strata_pipeline.ingest.witsml_time import load_well_time_series
from strata_pipeline.qc.align import align_well_channels
from strata_pipeline.qc.config import load_qc_config
from strata_pipeline.qc.pipeline import run_well_qc
from strata_pipeline.qc.qc_score import CoverageLevel
from strata_pipeline.qc.qc_score import qc_score as compute_qc_score
from strata_pipeline.rigstate.classify import run_rigstate
from strata_pipeline.rigstate.rules import CORE_CHANNELS

_CANONICAL_UNITS = {
    "HKLD": "kN", "BPOS": "m", "WOB": "kN", "RPM": "rpm", "TORQ": "kN.m", "SPP": "bar",
    "FLOWIN": "L/min", "BITDEPTH": "m", "HOLEDEPTH": "m", "ROP": "m/h", "MW_IN": "sg", "GAS": "%",
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_well_from_dataframes(
    well_id: str,
    long_time_df: pl.DataFrame,
    ddr_df: pl.DataFrame,
    out_dir: Path,
    reg: EvidenceRegistry,
    qc_cfg: dict[str, Any],
    rigstate_cfg: dict[str, Any],
    recon_cfg: dict[str, Any],
    travelling_block_weight: float,
    write_series: bool = True,
) -> dict[str, Any]:
    """Runs the full ingest(already loaded)->qc->align->rigstate->kpi/ilt/recon pipeline for one
    well and writes every `wells/<well_id>/*.json` file plus (if `write_series`) the series
    pyramid. Returns a summary used to build the cross-well `wells.json`/`eval.json` entries.
    Deterministic given the same inputs — no wall-clock or random values enter any computed
    number (`generated_at` timestamps in the caller's repro manifest are the only exception)."""
    well_dir = out_dir / "wells" / well_id

    qc_report = run_well_qc(long_time_df, qc_cfg)
    t, channels = align_well_channels(qc_report["channels"])

    ddr_rows_raw = ddr_df.to_dicts()

    if not t:
        # No surviving time-log data at all — every downstream file is honestly empty/null
        # rather than fabricated from nothing.
        intervals: list[Any] = []
    else:
        rigstate_run = run_rigstate(t, channels, travelling_block_weight, rigstate_cfg)
        intervals = rigstate_run.intervals

    kpi_report, connections, trips = build_kpis(well_id, t, channels, intervals, reg)
    ilt_report = build_ilt(well_id, kpi_report, connections, trips, intervals, ddr_rows_raw, reg)
    recon_report = build_reconciliation(well_id, ddr_rows_raw, intervals, recon_cfg, reg)

    _write_json(well_dir / "sections.json", build_sections_json())
    _write_json(well_dir / "depthtime.json", build_depthtime_json(t, channels))
    _write_json(well_dir / "rigstate.json", build_rigstate_json(intervals))
    _write_json(well_dir / "ddr.json", build_ddr_json(well_id, ddr_rows_raw))
    _write_json(well_dir / "kpis.json", kpi_report)
    _write_json(well_dir / "ilt.json", ilt_report)
    _write_json(out_dir / "reconciliation" / f"{well_id}.json", recon_report)

    if write_series and t:
        t0_ms = t[0].timestamp() * 1000
        series_channels: dict[str, Any] = {}
        for name, values in channels.items():
            arr = np.array([np.nan if v is None else v for v in values], dtype="f8")
            unit = _CANONICAL_UNITS.get(name, "1")
            series_channels[name] = export_channel_series(well_dir, name, unit, "pipeline:real", t0_ms, arr)
        _write_json(well_dir / "series" / "index.json", {"well": well_id, "channels": series_channels})

    well_duration_hours = (t[-1] - t[0]).total_seconds() / 3600.0 if len(t) > 1 else 0.0
    core_survived = [
        qc_report["channels"][c].survived_fraction for c in CORE_CHANNELS if c in qc_report["channels"]
    ]
    survived_fraction = sum(core_survived) / len(core_survived) if core_survived else 0.0
    core_gap_fraction = (
        min(1.0, qc_report["gap_hours"] / well_duration_hours) if well_duration_hours > 0 else 1.0
    )
    # Coverage is about what THIS exporter run actually produced, not everything the raw
    # archive has on disk — survey files exist for every real well (docs/DATA_INVENTORY.md) but
    # aren't ingested into this export yet, so they're "none" here, not "full".
    coverage: dict[str, CoverageLevel] = {
        "time_logs": "full" if t else "none",
        "daily_reports": "full" if ddr_rows_raw else "none",
        "depth_logs": "none",
        "tops": "none",
        "survey": "none",
        "mud": "none",
    }
    well_qc_score = compute_qc_score(coverage, qc_cfg["coverage_weights"], core_gap_fraction, survived_fraction)

    return {
        "well": well_id,
        "qc": {
            "well": well_id,
            "gap_hours": reg.quantity("qc.gaps", {"well": well_id}, qc_report["gap_hours"], "h", [], 2),
            "spikes_removed": qc_report["spikes_removed"],
            "unit_fixes": qc_report["unit_fixes"],
            "sentinels_removed": qc_report["sentinels_removed"],
        },
        "qc_score": well_qc_score,
        "coverage": coverage,
        "well_duration_hours": well_duration_hours,
        "reconciliation": recon_report,
        "n_rigstate_intervals": len(intervals),
        "n_ddr_rows": len(ddr_rows_raw),
    }


def run_well(
    well_id: str,
    witsml_root: Path,
    wellbore_name: str,
    ddr_dir: Path,
    ddr_file_prefix: str,
    out_dir: Path,
    reg: EvidenceRegistry,
    travelling_block_weight: float = 200.0,
    write_series: bool = True,
) -> dict[str, Any]:
    """Resolves real raw-data paths (as produced by T2.1's download + T2.2/T2.3's ingest) and
    runs `run_well_from_dataframes`. This is what the CLI (`make pipeline WELL=<id>`) calls."""
    qc_cfg = load_qc_config()
    long_time_df = load_well_time_series(witsml_root, wellbore_name)
    ddr_df = load_well_ddr(ddr_dir, ddr_file_prefix)

    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    raw_cfg = yaml.safe_load(config_path.read_text())
    rigstate_cfg = raw_cfg["rigstate"]
    recon_cfg = raw_cfg["recon"]

    return run_well_from_dataframes(
        well_id,
        long_time_df,
        ddr_df,
        out_dir,
        reg,
        qc_cfg,
        rigstate_cfg,
        recon_cfg,
        travelling_block_weight,
        write_series,
    )


__all__ = ["run_well", "run_well_from_dataframes"]
