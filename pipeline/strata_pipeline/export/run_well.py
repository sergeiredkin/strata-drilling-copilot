"""Top-level per-well orchestration — `make pipeline WELL=<id>`: ingest -> qc -> align ->
rigstate -> kpi/ilt/recon -> write the static-export files for one well
(docs/04_DATA_CONTRACTS.md §3). `run_well_from_dataframes` is the pure, testable core; `run_well`
resolves real on-disk paths and is what the CLI entry point calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import yaml

from strata_pipeline.events.extract import extract_issues
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
from strata_pipeline.formation.depth_features import BitInterval, build_depth_features
from strata_pipeline.formation.depth_series import build_depth_series
from strata_pipeline.formation.labels import FormationInterval, tops_to_intervals
from strata_pipeline.formation.report import build_formation_report
from strata_pipeline.ingest.ddr import load_well_bit_runs, load_well_ddr
from strata_pipeline.ingest.drilling_window import drilling_windows_from_ddr
from strata_pipeline.ingest.formation_tops import load_well_picks_csv, picks_for_wellbore
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


@dataclass(frozen=True)
class _QcStats:
    """The only pieces of `run_well_qc`'s report still needed past alignment — everything else
    (every channel's own pre-alignment grid) is redundant with `channels` once `align_well_channels`
    has run, and on a multi-year-gap real well that redundant data is gigabytes kept alive for
    the rest of the pipeline (rigstate, kpi, series export) for no reason. Extracting just these
    scalars lets the caller drop the full `qc_report` (see `run_well`/`run_well_from_dataframes`)."""

    core_survived_fraction: list[float]
    gap_hours: float
    spikes_removed: int
    unit_fixes: int
    sentinels_removed: int


def _qc_and_align(
    long_time_df: pl.DataFrame, qc_cfg: dict[str, Any]
) -> tuple[list[datetime], dict[str, np.ndarray], _QcStats]:
    qc_report = run_well_qc(long_time_df, qc_cfg)
    t, channels = align_well_channels(qc_report["channels"])
    stats = _QcStats(
        core_survived_fraction=[
            qc_report["channels"][c].survived_fraction for c in CORE_CHANNELS if c in qc_report["channels"]
        ],
        gap_hours=qc_report["gap_hours"],
        spikes_removed=qc_report["spikes_removed"],
        unit_fixes=qc_report["unit_fixes"],
        sentinels_removed=qc_report["sentinels_removed"],
    )
    return t, channels, stats


def _run_well_from_aligned(
    well_id: str,
    t: list[datetime],
    channels: dict[str, np.ndarray],
    qc_stats: _QcStats,
    ddr_df: pl.DataFrame,
    out_dir: Path,
    reg: EvidenceRegistry,
    qc_cfg: dict[str, Any],
    rigstate_cfg: dict[str, Any],
    recon_cfg: dict[str, Any],
    travelling_block_weight: float,
    write_series: bool,
    bit_intervals: list[BitInterval] | None = None,
    formation_tops: list[FormationInterval] | None = None,
    formation_tops_source: str | None = None,
) -> dict[str, Any]:
    """align -> rigstate -> kpi/ilt/recon -> write the static-export files, given QC's already
    -aligned output. Split out from `run_well_from_dataframes` so `run_well` can run ingest+QC
    in its own scope and drop the raw ingest DataFrame (`del long_time_df`) before this —
    otherwise that DataFrame stays referenced on `run_well`'s stack frame for this entire call
    (Python has no tail-call elimination), gigabytes held for no reason on a real multi-year-gap
    well.

    `bit_intervals`/`formation_tops` are optional (T11.1/T11.2): `formations.json` (ground-truth
    tops + descriptive stats, not the classifier's predictions — that needs a trained model,
    separate and not written here) is only written when both are given and non-empty, since
    without them there's nothing honest to compute."""
    well_dir = out_dir / "wells" / well_id
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

    ddr_json_rows = build_ddr_json(well_id, ddr_rows_raw)
    _write_json(well_dir / "sections.json", build_sections_json())
    _write_json(well_dir / "depthtime.json", build_depthtime_json(t, channels))
    _write_json(well_dir / "rigstate.json", build_rigstate_json(intervals))
    _write_json(well_dir / "ddr.json", ddr_json_rows)
    _write_json(well_dir / "kpis.json", kpi_report)
    _write_json(well_dir / "ilt.json", ilt_report)
    _write_json(out_dir / "reconciliation" / f"{well_id}.json", recon_report)

    if write_series and t:
        t0_ms = t[0].timestamp() * 1000
        series_channels: dict[str, Any] = {}
        for name, values in channels.items():
            # `values` is already a float32/NaN-gap numpy array (qc.align.align_well_channels) —
            # np.asarray is a no-op here, not a fresh Python-list-comprehension copy.
            arr = np.asarray(values, dtype="f8")
            unit = _CANONICAL_UNITS.get(name, "1")
            series_channels[name] = export_channel_series(
                well_dir, name, unit, "pipeline:real", t0_ms, arr,
                min_gap_seconds=qc_cfg["resample_gap_seconds"],
            )
        _write_json(well_dir / "series" / "index.json", {"well": well_id, "channels": series_channels})

    formation_report: dict[str, Any] | None = None
    if t:
        depth_table = build_depth_features(t, channels, bit_intervals=bit_intervals)
        if depth_table is not None:
            _write_json(well_dir / "depth_series.json", build_depth_series(well_id, channels, depth_table))
            if formation_tops:
                formation_report = build_formation_report(
                    well_id, depth_table, formation_tops, reg, source=formation_tops_source or "unknown"
                )
                _write_json(well_dir / "formations.json", formation_report)

    issues = extract_issues(well_id, ddr_json_rows, reg, formations=formation_report)

    well_duration_hours = (t[-1] - t[0]).total_seconds() / 3600.0 if len(t) > 1 else 0.0
    survived_fraction = (
        sum(qc_stats.core_survived_fraction) / len(qc_stats.core_survived_fraction)
        if qc_stats.core_survived_fraction
        else 0.0
    )
    # core_gap_fraction means "fraction of well time where a core channel is missing" (07 §3.6)
    # — R0 ("any core channel in gap") already is exactly that, measured once over the whole
    # timeline. qc_stats.gap_hours is NOT this: it sums every channel's own gap hours
    # independently, so it trivially exceeds well_duration_hours once there are more than a
    # couple of channels (every well's gap_hours > duration otherwise) and must never be used
    # as a 0-1 fraction here.
    r0_hours = sum(
        (iv.t1 - iv.t0).total_seconds() for iv in intervals if iv.rule_id == "R0"
    ) / 3600.0
    core_gap_fraction = min(1.0, r0_hours / well_duration_hours) if well_duration_hours > 0 else 1.0
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
            "gap_hours": reg.quantity("qc.gaps", {"well": well_id}, qc_stats.gap_hours, "h", [], 2),
            "spikes_removed": qc_stats.spikes_removed,
            "unit_fixes": qc_stats.unit_fixes,
            "sentinels_removed": qc_stats.sentinels_removed,
        },
        "qc_score": well_qc_score,
        "coverage": coverage,
        "well_duration_hours": well_duration_hours,
        "reconciliation": recon_report,
        "n_rigstate_intervals": len(intervals),
        "n_ddr_rows": len(ddr_rows_raw),
        "issues": issues,
    }


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
    bit_intervals: list[BitInterval] | None = None,
    formation_tops: list[FormationInterval] | None = None,
    formation_tops_source: str | None = None,
) -> dict[str, Any]:
    """Runs the full ingest(already loaded)->qc->align->rigstate->kpi/ilt/recon pipeline for one
    well and writes every `wells/<well_id>/*.json` file plus (if `write_series`) the series
    pyramid. Returns a summary used to build the cross-well `wells.json`/`eval.json` entries.
    Deterministic given the same inputs — no wall-clock or random values enter any computed
    number (`generated_at` timestamps in the caller's repro manifest are the only exception)."""
    t, channels, qc_stats = _qc_and_align(long_time_df, qc_cfg)
    return _run_well_from_aligned(
        well_id, t, channels, qc_stats, ddr_df, out_dir, reg, qc_cfg, rigstate_cfg, recon_cfg,
        travelling_block_weight, write_series,
        bit_intervals=bit_intervals,
        formation_tops=formation_tops,
        formation_tops_source=formation_tops_source,
    )


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
    well_picks_csv: Path | None = None,
) -> dict[str, Any]:
    """Resolves real raw-data paths (as produced by T2.1's download + T2.2/T2.3's ingest) and
    runs the qc->align->rigstate->kpi/ilt/recon pipeline. This is what the CLI (`make pipeline
    WELL=<id>`) calls.

    DDR loads first (cheap — a few thousand XML activity rows) so its drilling-coded activity
    windows (`ingest.drilling_window`) can bound the real-time log load — several real Volve
    wellbores carry years of mostly-irrelevant post-campaign history that would otherwise blow
    up QC/rig-state's per-sample processing to minutes and gigabytes for no benefit (found during
    the T3.7 smoke test). No drilling-coded DDR rows at all means no bound is available, not that
    nothing is in-window — the full log is loaded in that case. Bit records (for `formations.json`'s
    MSE/dxc) come from the same DDR files (`ingest.ddr.load_well_bit_runs`) at no extra file-read
    cost; `well_picks_csv` is a separate, optional provenance source (ADR 0010) — formations.json
    is only written when it's given and the well has at least one resolvable formation top.

    Runs QC+align itself (rather than delegating to `run_well_from_dataframes`) and `del`s the
    raw ingest DataFrame right after: calling through to `run_well_from_dataframes` would keep
    that DataFrame bound on this function's own stack frame for the entire nested call (Python
    has no tail-call elimination), which on a real multi-year-gap well (tens of millions of raw
    samples) is gigabytes held for no reason through rigstate/kpi/series-export."""
    qc_cfg = load_qc_config()
    ddr_df = load_well_ddr(ddr_dir, ddr_file_prefix)
    bit_rows = load_well_bit_runs(ddr_dir, ddr_file_prefix)
    bit_intervals = [BitInterval(r["md_top"], r["md_base"], r["diameter_in"]) for r in bit_rows]
    windows = drilling_windows_from_ddr(ddr_df) or None
    long_time_df = load_well_time_series(witsml_root, wellbore_name, windows=windows)
    t, channels, qc_stats = _qc_and_align(long_time_df, qc_cfg)
    del long_time_df

    formation_tops: list[FormationInterval] = []
    if well_picks_csv is not None and well_picks_csv.exists():
        picks_rows = load_well_picks_csv(well_picks_csv)
        picks = picks_for_wellbore(picks_rows, wellbore_name)
        formation_tops = tops_to_intervals(picks)

    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    raw_cfg = yaml.safe_load(config_path.read_text())
    rigstate_cfg = raw_cfg["rigstate"]
    recon_cfg = raw_cfg["recon"]

    return _run_well_from_aligned(
        well_id, t, channels, qc_stats, ddr_df, out_dir, reg, qc_cfg, rigstate_cfg, recon_cfg,
        travelling_block_weight, write_series,
        bit_intervals=bit_intervals,
        formation_tops=formation_tops,
        # Filename only, not the full path -- an absolute path would differ by machine and break
        # `make reproduce`'s byte-for-byte determinism guarantee for no benefit.
        formation_tops_source=well_picks_csv.name if well_picks_csv is not None else None,
    )


__all__ = ["run_well", "run_well_from_dataframes"]
