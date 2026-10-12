from datetime import UTC, datetime, timedelta

from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.export.real_well import (
    build_ddr_json,
    build_ilt,
    build_kpis,
    build_reconciliation,
    build_rigstate_json,
    gap_intervals_from_rigstate,
)
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 1, 1, tzinfo=UTC)

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


def _dt(s: float) -> datetime:
    return T0 + timedelta(seconds=s)


def _iv(t0_s: float, t1_s: float, state: str, rule_id: str = "R4") -> RigStateInterval:
    return RigStateInterval(
        t0=_dt(t0_s), t1=_dt(t1_s), state=state, rule_id=rule_id, confidence=1.0, back_reaming=False, n_samples=1
    )


def _ddr_row(t0_s: float, t1_s: float, code: str, npt: bool = False) -> dict:
    return {
        "t0": _dt(t0_s),
        "t1": _dt(t1_s),
        "normalized_code": code,
        "raw_code": f"drilling -- {code.lower()}",
        "md": 2000.0,
        "narrative": "",
        "report_date": "2013-01-01",
        "state": None,
        "npt_flag": npt,
    }


def test_build_rigstate_json_converts_to_epoch_ms_and_keeps_fields():
    intervals = [_iv(0, 60, "rotary_drilling")]
    out = build_rigstate_json(intervals)
    t0_ms = int(T0.timestamp() * 1000)
    assert out == [{"t0": t0_ms, "t1": t0_ms + 60_000, "state": "rotary_drilling", "p": 1.0, "rule_id": "R4"}]


def test_build_ddr_json_npt_defaults_from_npt_flag_field():
    rows = [_ddr_row(0, 600, "DRILL", npt=False), _ddr_row(600, 1200, "WAIT", npt=True)]
    out = build_ddr_json("W1", rows)
    assert out[0]["npt"] is False
    assert out[1]["npt"] is True
    assert out[0]["id"] == "ddr_W1_0"


def test_gap_intervals_from_rigstate_only_includes_r0():
    intervals = [_iv(0, 60, "rotary_drilling", "R4"), _iv(60, 120, "unknown", "R0")]
    gaps = gap_intervals_from_rigstate(intervals)
    assert gaps == [(_dt(60), _dt(120))]


def test_build_kpis_produces_cards_for_every_kpi_name():
    n = 400
    t = [_dt(i) for i in range(n)]
    channels = {
        "WOB": [20.0] * n,
        "BITDEPTH": [2000.0] * n,
    }
    intervals = [_iv(0, n - 1, "rotary_drilling", "R4")]
    reg = EvidenceRegistry()
    report, connections, trips = build_kpis("W1", t, channels, intervals, reg)
    names = {c["kpi"] for c in report["cards"]}
    assert names == {
        "conn_s2s", "conn_w2w", "trip_in_open", "trip_out_open",
        "trip_in_cased", "trip_out_cased", "flat_time_pct", "on_bottom_pct",
    }
    assert connections == []
    assert trips == []
    on_bottom_card = next(c for c in report["cards"] if c["kpi"] == "on_bottom_pct")
    assert on_bottom_card["value"]["value"] == 100.0


def test_build_kpis_null_card_when_no_connections_present():
    n = 100
    t = [_dt(i) for i in range(n)]
    channels = {"WOB": [20.0] * n, "BITDEPTH": [2000.0] * n}
    intervals = [_iv(0, n - 1, "circulating", "R7")]
    reg = EvidenceRegistry()
    report, _, _ = build_kpis("W1", t, channels, intervals, reg)
    conn_card = next(c for c in report["cards"] if c["kpi"] == "conn_s2s")
    assert conn_card["value"]["value"] is None
    assert conn_card["best"] is None


def test_build_ilt_sums_categories_and_matches_combine_ilt_total():
    n = 700
    t = [_dt(i) for i in range(n)]
    channels = {"WOB": [20.0] * n, "BITDEPTH": [2000.0] * n}
    intervals = [
        _iv(0, 99, "rotary_drilling", "R4"),
        _iv(100, 119, "connection", "R2"),
        _iv(120, 699, "rotary_drilling", "R4"),
    ]
    reg = EvidenceRegistry()
    kpi_report, connections, trips = build_kpis("W1", t, channels, intervals, reg)
    ddr_rows = [_ddr_row(0, 699, "DRILL")]
    ilt = build_ilt("W1", kpi_report, connections, trips, intervals, ddr_rows, reg)
    assert ilt["well"] == "W1"
    assert ilt["total"]["value"] is not None
    assert len(ilt["by_category"]) == 4
    assert ilt["by_section"][0]["section"] == "unknown"
    assert ilt["booked_npt"]["value"] == 0.0  # no npt_flag=True rows


def test_build_ilt_booked_npt_sums_only_flagged_rows():
    n = 10
    t = [_dt(i) for i in range(n)]
    channels: dict = {"WOB": [20.0] * n, "BITDEPTH": [2000.0] * n}
    intervals = [_iv(0, n - 1, "rotary_drilling", "R4")]
    reg = EvidenceRegistry()
    kpi_report, connections, trips = build_kpis("W1", t, channels, intervals, reg)
    ddr_rows = [_ddr_row(0, 3600, "WAIT", npt=True)]
    ilt = build_ilt("W1", kpi_report, connections, trips, intervals, ddr_rows, reg)
    assert ilt["booked_npt"]["value"] == 1.0


def test_build_reconciliation_matches_recon_module_shape():
    ddr_rows = [_ddr_row(0, 3600, "DRILL")]
    intervals = [_iv(0, 3600, "rotary_drilling", "R4")]
    reg = EvidenceRegistry()
    result = build_reconciliation("W1", ddr_rows, intervals, RECON_CFG, reg)
    assert result["scope"] == "W1"
    assert "DRILL" in result["rows"]
    assert result["per_well"][0]["well"] == "W1"
    assert result["per_well"][0]["agreement"]["value"] == 100.0
    drill_agreement = next(a for a in result["agreement"] if a["code"] == "DRILL")
    assert drill_agreement["pct"]["value"] == 100.0
    assert drill_agreement["booked"]["value"] == 1.0  # 1 hour booked
