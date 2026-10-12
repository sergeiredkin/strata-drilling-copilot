from datetime import UTC, datetime, timedelta

from strata_pipeline.kpi.connections import ConnectionKPI
from strata_pipeline.kpi.ilt.connections import ilt_connections
from strata_pipeline.kpi.ilt.flat_and_reaming import ilt_flat, ilt_reaming
from strata_pipeline.kpi.ilt.report import booked_npt_hours, combine_ilt
from strata_pipeline.kpi.ilt.trips import ilt_trips
from strata_pipeline.kpi.trips import TripSegment
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _dt(s: float) -> datetime:
    return T0 + timedelta(seconds=s)


def _iv(t0_s: float, t1_s: float, state: str, rule_id: str = "R4") -> RigStateInterval:
    return RigStateInterval(
        t0=_dt(t0_s), t1=_dt(t1_s), state=state, rule_id=rule_id, confidence=1.0, back_reaming=False, n_samples=1
    )


def test_ilt_connections_sums_excess_over_best():
    conns = [
        # 10 min, best 8 min -> 2 min excess.
        ConnectionKPI(t0=_dt(0), t1=_dt(600), conn_s2s_seconds=600.0, conn_w2w_seconds=None),
        # under best -> 0 excess.
        ConnectionKPI(t0=_dt(1000), t1=_dt(1300), conn_s2s_seconds=300.0, conn_w2w_seconds=None),
    ]
    result = ilt_connections(conns, ["8_1_2in", "8_1_2in"], {"8_1_2in": 480.0}, gap_intervals=[])
    assert result.total_seconds == 120.0
    assert result.n_included == 2
    assert result.excluded_gap_seconds == 0.0


def test_ilt_connections_excludes_ones_overlapping_a_gap():
    conns = [ConnectionKPI(t0=_dt(0), t1=_dt(600), conn_s2s_seconds=600.0, conn_w2w_seconds=None)]
    gaps = [(_dt(100), _dt(200))]
    result = ilt_connections(conns, ["8_1_2in"], {"8_1_2in": 480.0}, gap_intervals=gaps)
    assert result.n_included == 0
    assert result.n_excluded_by_gap == 1
    assert result.excluded_gap_seconds == 100.0
    assert result.total_seconds == 0.0


def test_ilt_connections_skips_section_with_no_best_known():
    conns = [ConnectionKPI(t0=_dt(0), t1=_dt(600), conn_s2s_seconds=600.0, conn_w2w_seconds=None)]
    result = ilt_connections(conns, ["unknown_section"], {}, gap_intervals=[])
    assert result.n_included == 0
    assert result.total_seconds == 0.0


def _trip(t0_s: float, t1_s: float, d0: float, d1: float, direction: str, section: str) -> TripSegment:
    return TripSegment(
        t0=_dt(t0_s), t1=_dt(t1_s), direction=direction, bitdepth_start=d0, bitdepth_end=d1,
        speed_m_per_h=abs(d1 - d0) / ((t1_s - t0_s) / 3600.0), section=section,
    )


def test_ilt_trips_sums_excess_time_over_ideal_at_best_speed():
    # 1000m trip_out over 2h real time; best open-hole speed = 1000 m/h -> ideal 1h -> 1h excess.
    trips = [_trip(0, 7200, 2000.0, 1000.0, "trip_out", "open")]
    result = ilt_trips(trips, ["8_1_2in"], {("8_1_2in", "open"): 1000.0}, gap_intervals=[])
    assert abs(result.total_seconds - 3600.0) < 1e-6
    assert result.n_included == 1


def test_ilt_trips_skips_mixed_section_trips():
    trips = [_trip(0, 3600, 2000.0, 1000.0, "trip_out", "mixed")]
    best_speeds = {("8_1_2in", "open"): 1000.0, ("8_1_2in", "cased"): 1000.0}
    result = ilt_trips(trips, ["8_1_2in"], best_speeds, gap_intervals=[])
    assert result.n_included == 0
    assert result.total_seconds == 0.0


def test_ilt_trips_excludes_ones_overlapping_a_gap():
    trips = [_trip(0, 3600, 2000.0, 1000.0, "trip_out", "open")]
    gaps = [(_dt(500), _dt(800))]
    result = ilt_trips(trips, ["8_1_2in"], {("8_1_2in", "open"): 1000.0}, gap_intervals=gaps)
    assert result.n_excluded_by_gap == 1
    assert result.excluded_gap_seconds == 300.0


def test_ilt_flat_sums_overlap_between_flat_states_and_drill_or_trip_ddr_rows():
    intervals = [_iv(0, 600, "circulating", "R7")]
    ddr_rows = [(_dt(300), _dt(900), "DRILL")]  # overlaps [300,600] = 300s
    result = ilt_flat(intervals, ddr_rows, gap_intervals=[])
    assert result.total_seconds == 300.0


def test_ilt_flat_ignores_ddr_rows_coded_circ():
    intervals = [_iv(0, 600, "circulating", "R7")]
    ddr_rows = [(_dt(0), _dt(600), "CIRC")]  # circulating booked AS circulating -> not ILT
    result = ilt_flat(intervals, ddr_rows, gap_intervals=[])
    assert result.total_seconds == 0.0


def test_ilt_flat_excludes_intervals_overlapping_a_gap():
    intervals = [_iv(0, 600, "circulating", "R7")]
    ddr_rows = [(_dt(0), _dt(600), "DRILL")]
    gaps = [(_dt(100), _dt(200))]
    result = ilt_flat(intervals, ddr_rows, gap_intervals=gaps)
    assert result.total_seconds == 0.0
    assert result.excluded_gap_seconds == 100.0


def test_ilt_reaming_sums_overlap_with_drill_coded_ddr_rows_only():
    intervals = [_iv(0, 600, "reaming", "R6")]
    ddr_rows = [(_dt(0), _dt(600), "DRILL"), (_dt(0), _dt(600), "TRIP")]
    result = ilt_reaming(intervals, ddr_rows, gap_intervals=[])
    # overlap only counted against the DRILL row (TRIP isn't in reaming's code set).
    assert result.total_seconds == 600.0


def test_booked_npt_hours_sums_only_npt_true_rows():
    rows = [(_dt(0), _dt(3600), True), (_dt(0), _dt(3600), False)]
    assert booked_npt_hours(rows) == 1.0


def test_combine_ilt_sums_four_categories_and_excluded_gap_hours():
    conns = [
        ConnectionKPI(t0=_dt(0), t1=_dt(600), conn_s2s_seconds=600.0, conn_w2w_seconds=None),
        ConnectionKPI(t0=_dt(1000), t1=_dt(1100), conn_s2s_seconds=100.0, conn_w2w_seconds=None),
    ]
    conn_result = ilt_connections(conns, ["S", "S"], {"S": 0.0}, gap_intervals=[(_dt(1000), _dt(1100))])
    trips = [_trip(0, 3600, 1000.0, 0.0, "trip_out", "open")]
    trip_result = ilt_trips(trips, ["S"], {("S", "open"): 1000.0}, gap_intervals=[])
    flat_result = ilt_flat([_iv(0, 600, "circulating", "R7")], [(_dt(0), _dt(600), "DRILL")], gap_intervals=[])
    reaming_result = ilt_reaming([_iv(0, 300, "reaming", "R6")], [(_dt(0), _dt(300), "DRILL")], gap_intervals=[])

    total = combine_ilt(conn_result, trip_result, flat_result, reaming_result)
    assert abs(total.connections_hours - 600.0 / 3600.0) < 1e-9
    assert abs(total.flat_hours - 600.0 / 3600.0) < 1e-9
    assert abs(total.reaming_hours - 300.0 / 3600.0) < 1e-9
    assert abs(total.excluded_gap_hours - 100.0 / 3600.0) < 1e-9
    assert abs(
        total.total_hours - (total.connections_hours + total.trips_hours + total.flat_hours + total.reaming_hours)
    ) < 1e-9
