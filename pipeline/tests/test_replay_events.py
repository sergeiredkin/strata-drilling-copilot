from datetime import UTC, datetime, timedelta

from strata_pipeline.export.replay_events import build_replay_events
from strata_pipeline.kpi.connections import ConnectionKPI
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 5, 20, 0, 0, tzinfo=UTC)


def _interval(offset_min: float, duration_min: float, state: str, rule_id: str = "R1") -> RigStateInterval:
    t0 = T0 + timedelta(minutes=offset_min)
    t1 = t0 + timedelta(minutes=duration_min)
    return RigStateInterval(t0=t0, t1=t1, state=state, rule_id=rule_id, confidence=1.0, back_reaming=False, n_samples=1)


def _kpi_report(best_min: float | None) -> dict:
    best = {"value": best_min, "unit": "min", "evidence_id": "ev_x"} if best_min else None
    return {"cards": [{"kpi": "conn_s2s", "best": best}]}


def test_build_replay_events_includes_a_state_event_per_interval() -> None:
    intervals = [_interval(0, 5, "rotary_drilling"), _interval(5, 5, "connection")]
    events = build_replay_events(intervals, [], [], _kpi_report(None))
    states = [e for e in events if e["type"] == "state"]
    assert [s["state"] for s in states] == ["rotary_drilling", "connection"]


def test_build_replay_events_emits_data_gap_for_r0_intervals() -> None:
    intervals = [_interval(0, 10, "unknown", rule_id="R0")]
    events = build_replay_events(intervals, [], [], _kpi_report(None))
    alerts = [e for e in events if e["type"] == "alert"]
    assert alerts[0]["alert"]["kind"] == "data_gap"


def test_build_replay_events_flat_time_requires_over_15_minutes() -> None:
    short = [_interval(0, 10, "circulating")]
    long = [_interval(0, 20, "circulating")]
    assert [e for e in build_replay_events(short, [], [], _kpi_report(None)) if e["type"] == "alert"] == []
    long_alerts = [e for e in build_replay_events(long, [], [], _kpi_report(None)) if e["type"] == "alert"]
    assert long_alerts[0]["alert"]["kind"] == "flat_time"


def test_build_replay_events_flat_time_excludes_data_gaps() -> None:
    # An "unknown" interval tagged R0 is a data gap, not flat time -- must not double-alert.
    intervals = [_interval(0, 30, "unknown", rule_id="R0")]
    events = build_replay_events(intervals, [], [], _kpi_report(None))
    kinds = [e["alert"]["kind"] for e in events if e["type"] == "alert"]
    assert kinds == ["data_gap"]


def test_build_replay_events_unreported_reaming_needs_ddr_drill_overlap() -> None:
    intervals = [_interval(0, 5, "reaming")]
    ddr_drill = [{"t0": T0, "t1": T0 + timedelta(minutes=5), "normalized_code": "DRILL"}]
    ddr_ream = [{"t0": T0, "t1": T0 + timedelta(minutes=5), "normalized_code": "REAM"}]
    events_drill = build_replay_events(intervals, ddr_drill, [], _kpi_report(None))
    events_ream = build_replay_events(intervals, ddr_ream, [], _kpi_report(None))
    assert any(e["alert"]["kind"] == "unreported_reaming" for e in events_drill if e["type"] == "alert")
    assert not any(e["type"] == "alert" for e in events_ream)


def test_build_replay_events_slow_connection_needs_1_5x_composite_best() -> None:
    conn_fast = ConnectionKPI(t0=T0, t1=T0 + timedelta(minutes=2), conn_s2s_seconds=120.0, conn_w2w_seconds=None)
    conn_slow = ConnectionKPI(t0=T0, t1=T0 + timedelta(minutes=5), conn_s2s_seconds=300.0, conn_w2w_seconds=None)
    report = _kpi_report(best_min=3.0)  # 1.5x = 4.5 min = 270s threshold
    fast_events = build_replay_events([], [], [conn_fast], report)
    slow_events = build_replay_events([], [], [conn_slow], report)
    assert not any(e["type"] == "alert" for e in fast_events)
    assert any(e["alert"]["kind"] == "slow_connection" for e in slow_events if e["type"] == "alert")


def test_build_replay_events_no_slow_connection_alerts_without_a_composite_best() -> None:
    conn = ConnectionKPI(t0=T0, t1=T0 + timedelta(minutes=10), conn_s2s_seconds=600.0, conn_w2w_seconds=None)
    events = build_replay_events([], [], [conn], _kpi_report(None))
    assert not any(e["type"] == "alert" for e in events)


def test_build_replay_events_sorted_by_time() -> None:
    intervals = [_interval(10, 5, "connection"), _interval(0, 5, "rotary_drilling")]
    events = build_replay_events(intervals, [], [], _kpi_report(None))
    ts = [e["t"] for e in events]
    assert ts == sorted(ts)
