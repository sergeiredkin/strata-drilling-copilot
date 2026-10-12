import json
import random
from datetime import UTC, datetime, timedelta

import polars as pl
from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.export.run_well import run_well_from_dataframes
from strata_pipeline.qc.config import load_qc_config

T0 = datetime(2013, 1, 1, tzinfo=UTC)

RIGSTATE_CFG = {
    "median_filter_seconds": 5.0,
    "block_velocity_window_seconds": 5.0,
    "slips_fallback_margin": 0.15,
    "on_bottom_m": 0.5,
    "near_bottom_m": 40.0,
    "rotating_rpm": 5.0,
    "pumping_lpm": 100.0,
    "moving_mps": 0.05,
    "out_of_hole_bitdepth_m": 30.0,
    "trip_direction_window_seconds": 600.0,
    "min_interval_seconds": 10.0,
    "confidence_margin_frac": 0.10,
}
RECON_CFG = {
    "boundary_slack_min": 5.0,
    "min_duration_min": 2.0,
    "expected_states": {
        "DRILL": ["rotary_drilling", "sliding", "connection"],
        "CIRC": ["circulating"],
        "TRIP": ["trip_in", "trip_out"],
        "REAM": ["reaming", "circulating"],
    },
    "included_codes": ["DRILL", "CIRC", "TRIP", "REAM"],
}


def _synthetic_long_df(n: int = 1200) -> pl.DataFrame:
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    rows = []
    # Values are already in canonical units (as witsml_time.py's ingest would store them);
    # raw_unit is just the provenance annotation QC carries along, not a re-conversion input.
    for seed, (channel, unit, value) in enumerate(
        [
            ("HKLD", "kN", 500.0),
            ("BPOS", "m", 10.0),
            ("WOB", "kN", 20.0),
            ("RPM", "rpm", 120.0),
            ("FLOWIN", "L/min", 800.0),
            ("BITDEPTH", "m", 2000.0),
            ("HOLEDEPTH", "m", 2000.2),
        ]
    ):
        rng = random.Random(seed)
        for ti in t:
            # Small deterministic noise so a real 20-minute run isn't flagged frozen_value
            # (QC correctly treats a perfectly flat-line sensor as stuck, per docs/07 §3.4) and
            # doesn't spuriously look bimodal to rigstate's HL_slips histogram calibration.
            jittered = value + rng.uniform(-0.5, 0.5) if value != 0.0 else 0.0
            rows.append(
                {
                    "t": ti,
                    "channel": channel,
                    "value": jittered,
                    "raw_mnemonic": channel,
                    "raw_unit": unit,
                    "source_log": "synthetic",
                }
            )
    return pl.DataFrame(rows)


def _synthetic_ddr_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "well": ["W1"],
            "wellbore": ["W1"],
            "report_date": ["2013-01-01"],
            "t0": [T0],
            "t1": [T0 + timedelta(seconds=1199)],
            "md": [2000.0],
            "raw_code": ["drilling -- drill"],
            "normalized_code": ["DRILL"],
            "state": ["ok"],
            "narrative": [""],
            "npt_flag": [None],
        }
    )


def test_run_well_from_dataframes_writes_all_expected_files(tmp_path):
    reg = EvidenceRegistry(git_commit="test")
    cfg = load_qc_config()
    summary = run_well_from_dataframes(
        "W1", _synthetic_long_df(), _synthetic_ddr_df(), tmp_path, reg, cfg, RIGSTATE_CFG, RECON_CFG, 200.0
    )
    well_dir = tmp_path / "wells" / "W1"
    for name in ("sections.json", "depthtime.json", "rigstate.json", "ddr.json", "kpis.json", "ilt.json"):
        assert (well_dir / name).exists(), name
    assert (tmp_path / "reconciliation" / "W1.json").exists()
    assert (well_dir / "series" / "index.json").exists()
    assert summary["n_rigstate_intervals"] >= 1
    assert summary["n_ddr_rows"] == 1
    assert summary["qc"]["well"] == "W1"


def test_run_well_from_dataframes_rigstate_classifies_as_rotary_drilling(tmp_path):
    reg = EvidenceRegistry(git_commit="test")
    cfg = load_qc_config()
    run_well_from_dataframes(
        "W1", _synthetic_long_df(), _synthetic_ddr_df(), tmp_path, reg, cfg, RIGSTATE_CFG, RECON_CFG, 200.0
    )
    rigstate = json.loads((tmp_path / "wells" / "W1" / "rigstate.json").read_text())
    assert rigstate[0]["state"] == "rotary_drilling"


def test_run_well_from_dataframes_is_deterministic(tmp_path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    cfg = load_qc_config()
    for out_dir in (out_a, out_b):
        reg = EvidenceRegistry(git_commit="test")
        run_well_from_dataframes(
            "W1", _synthetic_long_df(), _synthetic_ddr_df(), out_dir, reg, cfg, RIGSTATE_CFG, RECON_CFG, 200.0
        )
    for name in ("sections.json", "depthtime.json", "rigstate.json", "ddr.json", "kpis.json", "ilt.json"):
        a = (out_a / "wells" / "W1" / name).read_bytes()
        b = (out_b / "wells" / "W1" / name).read_bytes()
        assert a == b, name


def test_run_well_from_dataframes_handles_no_surviving_data_without_crashing(tmp_path):
    reg = EvidenceRegistry(git_commit="test")
    cfg = load_qc_config()
    empty_df = pl.DataFrame(
        schema={
            "t": pl.Datetime("us", "UTC"),
            "channel": pl.Utf8,
            "value": pl.Float64,
            "raw_mnemonic": pl.Utf8,
            "raw_unit": pl.Utf8,
            "source_log": pl.Utf8,
        }
    )
    empty_ddr = pl.DataFrame(
        schema={
            "well": pl.Utf8, "wellbore": pl.Utf8, "report_date": pl.Utf8,
            "t0": pl.Datetime("us", "UTC"), "t1": pl.Datetime("us", "UTC"), "md": pl.Float64,
            "raw_code": pl.Utf8, "normalized_code": pl.Utf8, "state": pl.Utf8, "narrative": pl.Utf8,
            "npt_flag": pl.Boolean,
        }
    )
    summary = run_well_from_dataframes(
        "W1", empty_df, empty_ddr, tmp_path, reg, cfg, RIGSTATE_CFG, RECON_CFG, 200.0
    )
    assert summary["n_rigstate_intervals"] == 0
    rigstate = json.loads((tmp_path / "wells" / "W1" / "rigstate.json").read_text())
    assert rigstate == []
