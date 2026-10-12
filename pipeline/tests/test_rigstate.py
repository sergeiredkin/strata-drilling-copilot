from datetime import UTC, datetime, timedelta

from strata_pipeline.rigstate.calibration import compute_hl_slips
from strata_pipeline.rigstate.classify import run_rigstate
from strata_pipeline.rigstate.flags import compute_flags
from strata_pipeline.rigstate.intervals import build_intervals
from strata_pipeline.rigstate.preprocess import block_velocity, median_filter
from strata_pipeline.rigstate.rules import classify_sample

T0 = datetime(2013, 1, 1, tzinfo=UTC)
CFG: dict = {
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


def _seconds(n: int) -> list[datetime]:
    return [T0 + timedelta(seconds=i) for i in range(n)]


def test_median_filter_smooths_single_sample_noise():
    values = [10.0, 10.0, 10.0, 10.0, 999.0, 10.0, 10.0, 10.0, 10.0]
    out = median_filter(values, window_seconds=5.0)
    assert out[4] == 10.0


def test_median_filter_preserves_none_as_none():
    values = [1.0, None, 3.0]
    out = median_filter(values, window_seconds=5.0)
    assert out[1] is None


def test_block_velocity_constant_position_is_zero():
    bpos = [10.0] * 20
    v = block_velocity(bpos, window_seconds=4.0)
    assert v[10] == 0.0


def test_block_velocity_sign_matches_direction_of_travel():
    bpos = [float(i) for i in range(20)]  # moving at +1 m/s
    v = block_velocity(bpos, window_seconds=4.0)
    assert abs(v[10] - 1.0) < 1e-9


def test_compute_hl_slips_fallback_when_no_two_mode_histogram():
    values = [500.0] * 100  # single constant value, no histogram shape at all
    slips = compute_hl_slips(values, travelling_block_weight=200.0, fallback_margin=0.15)
    assert slips.method == "travelling_block_fallback"
    assert abs(slips.hl_slips - 230.0) < 1e-9


def test_compute_hl_slips_finds_valley_between_two_modes():
    # Two clear clusters: ~100 (slips/off-bottom) and ~500 (on-bottom drilling), enough samples
    # per bin for a real histogram shape.
    values = [100.0 + (i % 5) for i in range(200)] + [500.0 + (i % 5) for i in range(200)]
    slips = compute_hl_slips(values, travelling_block_weight=200.0, fallback_margin=0.15)
    assert slips.method == "histogram_valley"
    assert 105 < slips.hl_slips < 495


def test_compute_flags_none_propagates_as_none_not_false():
    flags = compute_flags(
        hkld=None, bitdepth=2000.0, holedepth=2000.2, rpm=100.0, flowin=800.0, v=0.0, hl_slips=230.0, cfg=CFG
    )
    assert flags.in_slips is None
    assert flags.on_bottom is True


def test_classify_sample_r0_unknown_on_core_gap():
    raw = {"HKLD": None, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 100.0, "BITDEPTH": 2000.0, "HOLEDEPTH": 2000.2}
    flags = compute_flags(None, 2000.0, 2000.2, 100.0, 800.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "unknown"
    assert result.rule_id == "R0"


def test_classify_sample_r4_rotary_drilling():
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 120.0, "BITDEPTH": 2000.0, "HOLEDEPTH": 2000.2}
    flags = compute_flags(500.0, 2000.0, 2000.2, 120.0, 800.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "rotary_drilling"
    assert result.rule_id == "R4"


def test_classify_sample_r5_sliding_when_not_rotating():
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 2.0, "BITDEPTH": 2000.0, "HOLEDEPTH": 2000.2}
    flags = compute_flags(500.0, 2000.0, 2000.2, 2.0, 800.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "sliding"
    assert result.rule_id == "R5"


def test_classify_sample_r6_reaming_with_back_reaming_flag():
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 120.0, "BITDEPTH": 1950.0, "HOLEDEPTH": 2000.0}
    flags = compute_flags(500.0, 1950.0, 2000.0, 120.0, 800.0, 0.2, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "reaming"
    assert result.back_reaming is True


def test_classify_sample_r7_circulating_off_bottom_no_rotation():
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 0.0, "BITDEPTH": 1950.0, "HOLEDEPTH": 2000.0}
    flags = compute_flags(500.0, 1950.0, 2000.0, 0.0, 800.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "circulating"
    assert result.rule_id == "R7"


def test_classify_sample_r8_r9_trip_direction_follows_velocity_sign():
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 0.0, "RPM": 0.0, "BITDEPTH": 1950.0, "HOLEDEPTH": 2000.0}
    flags_in = compute_flags(500.0, 1950.0, 2000.0, 0.0, 0.0, -0.2, 230.0, CFG)
    assert classify_sample(raw, flags_in, None, 230.0, CFG).state == "trip_in"
    flags_out = compute_flags(500.0, 1950.0, 2000.0, 0.0, 0.0, 0.2, 230.0, CFG)
    assert classify_sample(raw, flags_out, None, 230.0, CFG).state == "trip_out"


def test_classify_sample_r1_out_of_hole_shallow_bitdepth_no_pumping():
    raw = {"HKLD": 50.0, "BPOS": 10.0, "FLOWIN": 0.0, "RPM": 0.0, "BITDEPTH": 10.0, "HOLEDEPTH": 10.0}
    flags = compute_flags(50.0, 10.0, 10.0, 0.0, 0.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "out_of_hole"
    assert result.rule_id == "R1"


def test_classify_sample_r2_connection_in_slips_near_bottom():
    raw = {"HKLD": 100.0, "BPOS": 10.0, "FLOWIN": 0.0, "RPM": 0.0, "BITDEPTH": 1990.0, "HOLEDEPTH": 2000.0}
    flags = compute_flags(100.0, 1990.0, 2000.0, 0.0, 0.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, None, 230.0, CFG)
    assert result.state == "connection"
    assert result.rule_id == "R2"


def test_classify_sample_r3_trip_uses_trip_direction_when_in_slips_far_from_bottom():
    raw = {"HKLD": 100.0, "BPOS": 10.0, "FLOWIN": 0.0, "RPM": 0.0, "BITDEPTH": 1000.0, "HOLEDEPTH": 2000.0}
    flags = compute_flags(100.0, 1000.0, 2000.0, 0.0, 0.0, 0.0, 230.0, CFG)
    result = classify_sample(raw, flags, "trip_out", 230.0, CFG)
    assert result.state == "trip_out"
    assert result.rule_id == "R3"


def test_build_intervals_merges_short_blip_into_previous_neighbour():
    results = [classify_sample(*_rotary_args()) for _ in range(20)]
    results += [classify_sample(*_circulating_args()) for _ in range(3)]  # 3s blip < 10s min
    results += [classify_sample(*_rotary_args()) for _ in range(20)]
    t = _seconds(len(results))
    intervals = build_intervals(t, results, min_interval_seconds=10.0, margin_frac=0.10)
    assert len(intervals) == 1
    assert intervals[0].state == "rotary_drilling"
    assert intervals[0].n_samples == 43


def test_build_intervals_keeps_connection_regardless_of_length():
    results = [classify_sample(*_rotary_args()) for _ in range(20)]
    results += [classify_sample(*_connection_args()) for _ in range(2)]  # short, but connection
    results += [classify_sample(*_rotary_args()) for _ in range(20)]
    t = _seconds(len(results))
    intervals = build_intervals(t, results, min_interval_seconds=10.0, margin_frac=0.10)
    assert [iv.state for iv in intervals] == ["rotary_drilling", "connection", "rotary_drilling"]


def test_build_intervals_confidence_reflects_margin_to_threshold():
    # Flowin exactly at the pumping threshold (100) is borderline for R7's deciding margin;
    # well above it (800) is decisive.
    raw_borderline = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 100.0, "RPM": 0.0, "BITDEPTH": 1950.0, "HOLEDEPTH": 2000.0}
    flags_borderline = compute_flags(500.0, 1950.0, 2000.0, 0.0, 100.1, 0.0, 230.0, CFG)
    result_borderline = classify_sample(raw_borderline, flags_borderline, None, 230.0, CFG)
    t = _seconds(1)
    intervals = build_intervals(t, [result_borderline], min_interval_seconds=10.0, margin_frac=0.10)
    assert intervals[0].confidence == 0.0


def _rotary_args() -> tuple:
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 120.0, "BITDEPTH": 2000.0, "HOLEDEPTH": 2000.2}
    flags = compute_flags(500.0, 2000.0, 2000.2, 120.0, 800.0, 0.0, 230.0, CFG)
    return raw, flags, None, 230.0, CFG


def _circulating_args() -> tuple:
    raw = {"HKLD": 500.0, "BPOS": 10.0, "FLOWIN": 800.0, "RPM": 0.0, "BITDEPTH": 1950.0, "HOLEDEPTH": 2000.0}
    flags = compute_flags(500.0, 1950.0, 2000.0, 0.0, 800.0, 0.0, 230.0, CFG)
    return raw, flags, None, 230.0, CFG


def _connection_args() -> tuple:
    raw = {"HKLD": 100.0, "BPOS": 10.0, "FLOWIN": 0.0, "RPM": 0.0, "BITDEPTH": 1990.0, "HOLEDEPTH": 2000.0}
    flags = compute_flags(100.0, 1990.0, 2000.0, 0.0, 0.0, 0.0, 230.0, CFG)
    return raw, flags, None, 230.0, CFG


def test_run_rigstate_end_to_end_rotary_drilling_well():
    n = 1200
    t = _seconds(n)
    channels = {
        "HKLD": [500.0] * n,
        "BPOS": [10.0] * n,
        "FLOWIN": [800.0] * n,
        "RPM": [120.0] * n,
        "BITDEPTH": [2000.0] * n,
        "HOLEDEPTH": [2000.2] * n,
    }
    run = run_rigstate(t, channels, travelling_block_weight=200.0, cfg=CFG)
    assert len(run.intervals) == 1
    assert run.intervals[0].state == "rotary_drilling"
    assert run.intervals[0].confidence == 1.0


def test_run_rigstate_gap_in_core_channel_yields_unknown_interval():
    n = 100
    t = _seconds(n)
    channels = {
        "HKLD": [500.0] * n,
        "BPOS": [10.0] * n,
        "FLOWIN": [800.0] * n,
        "RPM": [120.0] * n,
        "BITDEPTH": [None] * n,
        "HOLEDEPTH": [2000.2] * n,
    }
    run = run_rigstate(t, channels, travelling_block_weight=200.0, cfg=CFG)
    assert len(run.intervals) == 1
    assert run.intervals[0].state == "unknown"
    assert run.intervals[0].rule_id == "R0"
