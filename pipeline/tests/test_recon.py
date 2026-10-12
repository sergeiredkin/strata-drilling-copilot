from datetime import UTC, datetime, timedelta

from strata_pipeline.recon.ddr_codes import load_ddr_code_rules, normalize_code
from strata_pipeline.recon.reconciliation import (
    DdrRow,
    apply_boundary_slack,
    compute_reconciliation,
    find_mismatch_runs,
    measured_minutes_by_state,
)
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 1, 1, tzinfo=UTC)
CFG = {
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


def _dt(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _iv(t0_min: float, t1_min: float, state: str) -> RigStateInterval:
    return RigStateInterval(
        t0=_dt(t0_min), t1=_dt(t1_min), state=state, rule_id="R4", confidence=1.0, back_reaming=False, n_samples=1
    )


def test_load_ddr_code_rules_matches_ingest_ddr_module():
    from strata_pipeline.ingest.ddr import normalize_code as ingest_normalize_code

    rules = load_ddr_code_rules()
    assert normalize_code("Drilling -- Drill", rules) == "DRILL"
    assert normalize_code("Drilling -- Drill", rules) == ingest_normalize_code("Drilling -- Drill")


def test_apply_boundary_slack_trims_both_ends():
    trimmed = apply_boundary_slack(_dt(0), _dt(60), slack_min=5.0)
    assert trimmed == (_dt(5), _dt(55))


def test_apply_boundary_slack_none_when_row_too_short():
    assert apply_boundary_slack(_dt(0), _dt(8), slack_min=5.0) is None


def test_measured_minutes_by_state_sums_overlap_per_state():
    intervals = [_iv(0, 10, "rotary_drilling"), _iv(10, 20, "circulating")]
    minutes = measured_minutes_by_state(intervals, _dt(5), _dt(15))
    assert minutes["rotary_drilling"] == 5.0
    assert minutes["circulating"] == 5.0


def test_compute_reconciliation_perfect_drill_agreement():
    ddr_rows = [DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL")]
    intervals = [_iv(0, 60, "rotary_drilling")]
    result = compute_reconciliation(
        ddr_rows, intervals, CFG["expected_states"], CFG["included_codes"], CFG["boundary_slack_min"]
    )
    drill_agreement = next(a for a in result.agreement if a.code == "DRILL")
    assert drill_agreement.pct == 100.0
    assert drill_agreement.booked_minutes == 60.0
    assert result.per_well_agreement == 100.0
    assert result.cells["DRILL"]["rotary_drilling"].pct == 100.0


def test_compute_reconciliation_detects_partial_mismatch():
    # 60 min DRILL row, trimmed to [5,55] (50 min). Of that, 40 min rotary_drilling (expected),
    # 10 min circulating (not expected for DRILL) -> 80% agreement.
    ddr_rows = [DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL")]
    intervals = [_iv(0, 45, "rotary_drilling"), _iv(45, 60, "circulating")]
    result = compute_reconciliation(
        ddr_rows, intervals, CFG["expected_states"], CFG["included_codes"], CFG["boundary_slack_min"]
    )
    drill_agreement = next(a for a in result.agreement if a.code == "DRILL")
    assert abs(drill_agreement.pct - 80.0) < 1e-9


def test_compute_reconciliation_excludes_codes_with_no_rows_from_weighting():
    ddr_rows = [DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL")]
    intervals = [_iv(0, 60, "rotary_drilling")]
    result = compute_reconciliation(
        ddr_rows, intervals, CFG["expected_states"], CFG["included_codes"], CFG["boundary_slack_min"]
    )
    circ_agreement = next(a for a in result.agreement if a.code == "CIRC")
    assert circ_agreement.pct is None
    assert circ_agreement.booked_minutes == 0.0
    assert result.per_well_agreement == 100.0  # unaffected by the zero-weight CIRC code


def test_compute_reconciliation_per_well_is_minute_weighted():
    ddr_rows = [
        DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL"),  # 50 min outside slack, 100%
        DdrRow(t0=_dt(60), t1=_dt(660), normalized_code="CIRC"),  # 590 min outside slack, 0%
    ]
    intervals = [_iv(0, 60, "rotary_drilling"), _iv(60, 660, "trip_in")]
    result = compute_reconciliation(
        ddr_rows, intervals, CFG["expected_states"], CFG["included_codes"], CFG["boundary_slack_min"]
    )
    # Heavily weighted toward the long, 0%-agreement CIRC row.
    assert result.per_well_agreement is not None
    assert result.per_well_agreement < 20.0


def test_find_mismatch_runs_flags_long_run_outside_expected_states():
    ddr_row = DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL")
    intervals = [_iv(0, 45, "rotary_drilling"), _iv(45, 55, "circulating")]
    runs = find_mismatch_runs(
        intervals, ddr_row, {"rotary_drilling", "sliding", "connection"}, slack_min=5.0, min_duration_min=2.0
    )
    assert len(runs) == 1
    assert runs[0].state == "circulating"
    assert runs[0].t0 == _dt(45)
    assert runs[0].t1 == _dt(55)


def test_find_mismatch_runs_ignores_short_runs_under_min_duration():
    ddr_row = DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL")
    intervals = [_iv(0, 50, "rotary_drilling"), _iv(50, 51, "circulating"), _iv(51, 60, "rotary_drilling")]
    runs = find_mismatch_runs(
        intervals, ddr_row, {"rotary_drilling", "sliding", "connection"}, slack_min=5.0, min_duration_min=2.0
    )
    assert runs == []


def test_find_mismatch_runs_respects_boundary_slack():
    # The only "mismatch" state is right at the row's start, inside the 5-min slack -> ignored.
    ddr_row = DdrRow(t0=_dt(0), t1=_dt(60), normalized_code="DRILL")
    intervals = [_iv(0, 4, "circulating"), _iv(4, 60, "rotary_drilling")]
    runs = find_mismatch_runs(
        intervals, ddr_row, {"rotary_drilling", "sliding", "connection"}, slack_min=5.0, min_duration_min=2.0
    )
    assert runs == []
