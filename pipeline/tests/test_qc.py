from datetime import UTC, datetime, timedelta

import polars as pl
from strata_pipeline.qc.config import load_qc_config
from strata_pipeline.qc.frozen import frozen_value_mask
from strata_pipeline.qc.pipeline import run_channel_qc, run_well_qc
from strata_pipeline.qc.qc_score import qc_score
from strata_pipeline.qc.reconcile import pick_source_per_channel
from strata_pipeline.qc.resample import find_no_data_gaps, resample_to_grid
from strata_pipeline.qc.sentinels import sentinel_mask
from strata_pipeline.qc.spikes import hampel_spike_mask
from strata_pipeline.qc.units import detect_and_fix_unit

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _seconds(n: int) -> list[datetime]:
    return [T0 + timedelta(seconds=i) for i in range(n)]


def test_sentinel_mask_flags_known_fill_values_and_nan():
    values = pl.Series([1.0, -999.25, 2.0, -9999.0, 9999.0, float("nan"), 3.0], dtype=pl.Float64)
    mask = sentinel_mask(values, [-999.25, -9999, 9999])
    assert mask.to_list() == [False, True, False, True, True, True, False]


def test_hampel_spike_mask_flags_isolated_outlier_not_a_sustained_excursion():
    base = [50.0] * 40
    series = list(base)
    series[20] = 500.0  # isolated single-sample spike
    mask = hampel_spike_mask(series, window=31, threshold=6.0)
    assert mask[20] is True
    assert all(not m for i, m in enumerate(mask) if i != 20)

    sustained = list(base)
    for i in range(20, 23):
        sustained[i] = 500.0  # a real multi-sample excursion, not a spike
    mask2 = hampel_spike_mask(sustained, window=31, threshold=6.0)
    assert not any(mask2[20:23])


def test_frozen_value_mask_flags_long_held_nonzero_value_only():
    t = _seconds(700)
    values: list[float | None] = [float(i % 5) for i in range(700)]
    for i in range(100, 500):  # held at 7.0 for 400s > 300s threshold
        values[i] = 7.0
    for i in range(600, 610):  # held for only 10s, below threshold
        values[i] = 9.0
    mask = frozen_value_mask(t, values, min_seconds=300.0)
    assert all(mask[100:500])
    assert not any(mask[600:610])
    assert not mask[0]


def test_frozen_value_mask_ignores_zero_as_frozen():
    t = _seconds(400)
    values = [0.0] * 400
    mask = frozen_value_mask(t, values, min_seconds=300.0)
    assert not any(mask)


def test_detect_and_fix_unit_corrects_hookload_mislabelled_as_lbf():
    cfg = {"unit_fix_rules": {"HKLD": {"median_above": 1500, "assume_raw_unit": "lbf", "factor_to_kn": 0.0044482216}}}
    values = [2000.0] * 10  # median 2000 > 1500 threshold => assume lbf, convert to kN
    fixed, event = detect_and_fix_unit(values, "HKLD", cfg)
    assert event is not None
    assert event.assumed_raw_unit == "lbf"
    assert abs(fixed[0] - 2000.0 * 0.0044482216) < 1e-9


def test_detect_and_fix_unit_leaves_plausible_values_untouched():
    cfg = {"unit_fix_rules": {"HKLD": {"median_above": 1500, "assume_raw_unit": "lbf", "factor_to_kn": 0.0044482216}}}
    values = [800.0] * 10
    fixed, event = detect_and_fix_unit(values, "HKLD", cfg)
    assert event is None
    assert fixed == values


def test_resample_to_grid_snaps_to_nearest_second():
    t = [T0, T0 + timedelta(seconds=1, milliseconds=100), T0 + timedelta(seconds=2)]
    values = [1.0, 2.0, 3.0]
    grid_t, grid_v = resample_to_grid(t, values, grid_seconds=1.0)
    assert len(grid_t) == 3
    assert grid_v == [1.0, 2.0, 3.0]


def test_find_no_data_gaps_reports_only_holes_over_threshold():
    # Build a 20 s grid manually: samples at 0-2s and 10-19s, hole of 7s (3..9) in between.
    grid_t = _seconds(20)
    grid_v: list[float | None] = [None] * 20
    for i in [0, 1, 2, *range(10, 20)]:
        grid_v[i] = 1.0
    gaps = find_no_data_gaps(grid_t, grid_v, gap_seconds=5.0)
    assert len(gaps) == 1
    assert gaps[0].reason == "no_data"
    assert gaps[0].t0 == grid_t[3]
    assert gaps[0].t1 == grid_t[9]


def test_find_no_data_gaps_ignores_short_holes():
    grid_t = _seconds(10)
    grid_v: list[float | None] = [1.0] * 10
    grid_v[4] = None  # single missing second, well under the 5s threshold
    gaps = find_no_data_gaps(grid_t, grid_v, gap_seconds=5.0)
    assert gaps == []


def test_pick_source_per_channel_keeps_richest_source_and_breaks_ties_alphabetically():
    df = pl.DataFrame(
        {
            "t": _seconds(6),
            "channel": ["RPM", "RPM", "RPM", "RPM", "RPM", "RPM"],
            "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "raw_mnemonic": ["SURF_RPM"] * 6,
            "raw_unit": ["rpm"] * 6,
            "source_log": ["logA", "logA", "logA", "logB", "logB", "logC"],
        }
    )
    kept, report = pick_source_per_channel(df)
    assert set(kept["source_log"].unique()) == {"logA"}
    assert len(kept) == 3
    assert report["RPM"] == {"logA": 3, "logB": 2, "logC": 1}

    # Tie case: logX and logY both have 2 samples -> alphabetically first (logX) wins.
    tie_df = pl.DataFrame(
        {
            "t": _seconds(4),
            "channel": ["WOB"] * 4,
            "value": [1.0, 2.0, 3.0, 4.0],
            "raw_mnemonic": ["WOB_AVG"] * 4,
            "raw_unit": ["kN"] * 4,
            "source_log": ["logY", "logY", "logX", "logX"],
        }
    )
    kept2, _ = pick_source_per_channel(tie_df)
    assert set(kept2["source_log"].unique()) == {"logX"}


def test_run_channel_qc_end_to_end_known_answer():
    n = 700
    t = _seconds(n)
    values = [50.0] * n
    values[100] = -999.25  # sentinel
    values[200] = 900.0  # isolated spike
    for i in range(300, 650):  # frozen run, 350s > 300s threshold
        values[i] = 77.0
    cfg = {
        "unit_fix_rules": {},
        "sentinels": [-999.25, -9999, 9999],
        "spike_hampel_window": 31,
        "spike_hampel_threshold_mad": 6.0,
        "frozen_min_seconds": 300.0,
        "resample_grid_seconds": 1.0,
        "resample_gap_seconds": 5.0,
    }
    result = run_channel_qc(t, values, "HKLD", cfg)
    assert result.reason_counts.get("sentinel") == 1
    assert result.reason_counts.get("removed_spike") == 1
    assert result.reason_counts.get("frozen_value") == 350
    assert result.unit_fix is None
    expected_survived = (n - 1 - 1 - 350) / n
    assert abs(result.survived_fraction - expected_survived) < 1e-9


def test_run_well_qc_aggregates_report_matching_eval_report_contract_shape():
    n = 100
    t = _seconds(n)
    df = pl.DataFrame(
        {
            "t": t,
            "channel": ["HKLD"] * n,
            "value": [50.0] * n,
            "raw_mnemonic": ["HKLD_AVG"] * n,
            "raw_unit": ["N"] * n,
            "source_log": ["logA"] * n,
        }
    )
    cfg = {
        "unit_fix_rules": {},
        "sentinels": [-999.25, -9999, 9999],
        "spike_hampel_window": 31,
        "spike_hampel_threshold_mad": 6.0,
        "frozen_min_seconds": 300.0,
        "resample_grid_seconds": 1.0,
        "resample_gap_seconds": 5.0,
    }
    report = run_well_qc(df, cfg)
    for key in ("gap_hours", "spikes_removed", "unit_fixes", "sentinels_removed"):
        assert key in report
    assert report["spikes_removed"] == 0
    assert report["sentinels_removed"] == 0
    assert report["gap_hours"] == 0.0


def test_qc_score_matches_spec_formula():
    coverage = {"time_logs": "full", "daily_reports": "partial", "depth_logs": "none"}
    weights = {"time_logs": 0.35, "daily_reports": 0.20, "depth_logs": 0.15}
    score = qc_score(coverage, weights, core_gap_fraction=0.1, survived_fraction=0.9)
    coverage_weighted = 0.35 * 1.0 + 0.20 * 0.5 + 0.15 * 0.0
    expected = coverage_weighted * (1 - 0.1) * 0.9
    assert abs(score - expected) < 1e-9


def test_load_qc_config_has_all_keys_rules_depend_on():
    cfg = load_qc_config()
    for key in (
        "plausible_ranges",
        "unit_fix_rules",
        "sentinels",
        "spike_hampel_window",
        "spike_hampel_threshold_mad",
        "frozen_min_seconds",
        "resample_grid_seconds",
        "resample_gap_seconds",
        "core_channels",
        "coverage_weights",
    ):
        assert key in cfg
    run_channel_qc(_seconds(10), [50.0] * 10, "HKLD", cfg)  # smoke test: real config is usable
