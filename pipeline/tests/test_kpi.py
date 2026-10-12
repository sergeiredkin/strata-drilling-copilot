from datetime import UTC, datetime, timedelta

from strata_pipeline.kpi.composite_best import compute_composite_best, compute_composite_best_by_section
from strata_pipeline.kpi.connections import compute_connections, expand_states
from strata_pipeline.kpi.distributions import Sample, compute_distribution, percentile
from strata_pipeline.kpi.flat_time import flat_time_pct, on_bottom_pct, total_valid_seconds
from strata_pipeline.kpi.trips import compute_trips
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _iv(t0_s: float, t1_s: float, state: str, rule_id: str = "R4") -> RigStateInterval:
    return RigStateInterval(
        t0=T0 + timedelta(seconds=t0_s),
        t1=T0 + timedelta(seconds=t1_s),
        state=state,
        rule_id=rule_id,
        confidence=1.0,
        back_reaming=False,
        n_samples=int(t1_s - t0_s) + 1,
    )


def test_percentile_matches_known_values():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 0.0) == 10.0
    assert percentile(values, 100.0) == 50.0
    assert percentile(values, 50.0) == 30.0


def test_percentile_empty_is_none():
    assert percentile([], 50.0) is None


def test_compute_distribution_known_five_number_summary():
    samples = [Sample(value=float(v), window=v) for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    dist = compute_distribution(samples)
    assert dist is not None
    assert dist.n == 10
    assert dist.min == 1.0
    assert dist.max == 10.0
    assert dist.median == 5.5


def test_compute_distribution_flags_outliers_above_q3_plus_1_5_iqr():
    samples = [Sample(value=float(v), window=v) for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]]
    dist = compute_distribution(samples)
    assert dist is not None
    assert len(dist.outliers) == 1
    assert dist.outliers[0].value == 100.0
    assert dist.outliers[0].window == 100


def test_compute_distribution_empty_is_none():
    assert compute_distribution([]) is None


def test_total_valid_seconds_excludes_r0_gaps():
    intervals = [_iv(0, 99, "rotary_drilling", "R4"), _iv(100, 199, "unknown", "R0")]
    assert total_valid_seconds(intervals) == 99.0  # t1 - t0 convention (same as qc/rigstate)


def test_flat_time_pct_counts_circulating_reaming_idle_and_out_of_hole():
    intervals = [
        _iv(0, 99, "rotary_drilling", "R4"),  # 100s on-bottom, not flat
        _iv(100, 199, "circulating", "R7"),  # 100s flat
        _iv(200, 299, "unknown", "R10"),  # 100s flat (idle, not a gap)
        _iv(300, 399, "unknown", "R0"),  # excluded entirely (gap)
    ]
    pct = flat_time_pct(intervals)
    assert pct is not None
    assert abs(pct - 200.0 / 300.0) < 1e-9


def test_flat_time_pct_none_when_entirely_gap():
    intervals = [_iv(0, 99, "unknown", "R0")]
    assert flat_time_pct(intervals) is None


def test_on_bottom_pct_counts_rotary_and_sliding_only():
    intervals = [
        _iv(0, 99, "rotary_drilling", "R4"),
        _iv(100, 199, "sliding", "R5"),
        _iv(200, 299, "circulating", "R7"),
    ]
    pct = on_bottom_pct(intervals)
    assert pct is not None
    assert abs(pct - 200.0 / 300.0) < 1e-9


def test_expand_states_maps_each_sample_to_its_covering_interval():
    intervals = [_iv(0, 4, "rotary_drilling"), _iv(5, 9, "circulating", "R7")]
    t = [T0 + timedelta(seconds=i) for i in range(10)]
    states = expand_states(intervals, t)
    assert states[0] == "rotary_drilling"
    assert states[4] == "rotary_drilling"
    assert states[5] == "circulating"
    assert states[9] == "circulating"


def test_compute_connections_conn_s2s_and_conn_w2w():
    # 0-99: rotary_drilling with WOB>5 (on-bottom), 100-119: connection, 120-199: rotary again.
    n = 200
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    wob = [20.0] * n
    wob[90:100] = [0.0] * 10  # WOB drops to zero right before the connection starts
    wob[100:125] = [0.0] * 25  # and stays zero a bit after it ends
    intervals = [
        _iv(0, 99, "rotary_drilling", "R4"),
        _iv(100, 119, "connection", "R2"),
        _iv(120, 199, "rotary_drilling", "R4"),
    ]
    states = expand_states(intervals, t)
    conns = compute_connections(t, wob, states, intervals, wob_threshold_kn=5.0)
    assert len(conns) == 1
    assert conns[0].conn_s2s_seconds == 19.0  # t1 - t0 convention
    # last WOB>5 sample before connection: index 89 (t=89s); first after: index 125 (t=125s).
    assert conns[0].conn_w2w_seconds == 125.0 - 89.0


def test_compute_connections_w2w_none_when_no_on_bottom_sample_found():
    n = 50
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    wob = [0.0] * n
    intervals = [_iv(0, 49, "connection", "R2")]
    states = expand_states(intervals, t)
    conns = compute_connections(t, wob, states, intervals)
    assert conns[0].conn_w2w_seconds is None


def test_compute_trips_speed_and_section_classification():
    n = 3700
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    bitdepth: list[float | None] = [2000.0] * n
    for i in range(0, 3600):
        bitdepth[i] = 2000.0 - (i / 3600.0) * 1000.0  # pulls out 1000m over exactly 1 hour
    intervals = [_iv(0, 3599, "trip_out", "R9")]
    trips = compute_trips(t, bitdepth, intervals, casing_shoe_md=1500.0)
    assert len(trips) == 1
    assert abs(trips[0].speed_m_per_h - 1000.0) < 1.0
    assert trips[0].section == "mixed"  # spans 1000m (open) to 2000m (cased)


def test_compute_trips_merges_short_in_slips_gap_same_direction():
    n = 1300
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    bitdepth: list[float | None] = [2000.0] * n
    intervals = [
        _iv(0, 599, "trip_in", "R8"),
        _iv(600, 659, "connection", "R2"),  # 60s gap, well under the 10-min allowance
        _iv(660, 1299, "trip_in", "R8"),
    ]
    trips = compute_trips(t, bitdepth, intervals, casing_shoe_md=None)
    assert len(trips) == 1
    assert trips[0].t0 == t[0]
    assert trips[0].t1 == t[-1]


def test_compute_trips_does_not_merge_across_long_gap():
    n = 2000
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    bitdepth: list[float | None] = [2000.0] * n
    intervals = [
        _iv(0, 599, "trip_in", "R8"),
        _iv(600, 1599, "connection", "R2"),  # 1000s > 600s allowance
        _iv(1600, 1999, "trip_in", "R8"),
    ]
    trips = compute_trips(t, bitdepth, intervals, casing_shoe_md=None)
    assert len(trips) == 2


def test_compute_composite_best_uses_section_when_n_meets_minimum():
    section_values = list(range(1, 21))  # n=20 durations, 1..20
    well_values = section_values + [1000.0]  # well level would be skewed if used
    result = compute_composite_best([float(v) for v in section_values], [float(v) for v in well_values], "duration")
    assert result.used_well_level_fallback is False
    assert result.n == 20


def test_compute_composite_best_falls_back_to_well_level_when_n_below_minimum():
    section_values = [1.0, 2.0, 3.0]  # n=3 < 10
    well_values = [float(v) for v in range(1, 21)]
    result = compute_composite_best(section_values, well_values, "speed")
    assert result.used_well_level_fallback is True
    assert result.n == 20


def test_compute_composite_best_by_section_pools_well_level_fallback():
    values_by_section = {
        "12_1_4in": [1.0, 2.0, 3.0],  # below min_n, falls back
        "8_1_2in": [float(v) for v in range(1, 15)],  # above min_n, uses section
    }
    results = compute_composite_best_by_section(values_by_section, "duration")
    assert results["8_1_2in"].used_well_level_fallback is False
    assert results["12_1_4in"].used_well_level_fallback is True
    assert results["12_1_4in"].n == 3 + 14
