from datetime import UTC, datetime, timedelta

import numpy as np
from strata_pipeline.events.precursors import build_precursors
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 5, 20, 12, 0, tzinfo=UTC)


def _synthetic_well(n_hours: int = 20) -> tuple[list[datetime], dict[str, np.ndarray]]:
    n = n_hours * 3600
    t = [T0 + timedelta(seconds=i) for i in range(n)]
    channels = {
        "HKLD": np.full(n, 500.0),
        "TORQ": np.full(n, 15.0),
        "SPP": np.full(n, 180.0),
        "BITDEPTH": np.full(n, 2600.0),
    }
    return t, channels


def _interval(t0: datetime, t1: datetime, state: str) -> RigStateInterval:
    return RigStateInterval(
        t0=t0, t1=t1, state=state, rule_id="R_test", confidence=1.0, back_reaming=False, n_samples=1
    )


def _issue(t0_ms: float, md: float | None = 2600.0) -> dict:
    return {"id": "issue_1", "t0": t0_ms, "md": md}


def test_build_precursors_returns_none_without_md() -> None:
    t, channels = _synthetic_well()
    issue = _issue(t[-1].timestamp() * 1000, md=None)
    assert build_precursors(issue, t, channels, []) is None


def test_build_precursors_returns_none_without_time_series() -> None:
    assert build_precursors(_issue(0.0), [], {}, []) is None


def test_build_precursors_returns_none_when_event_predates_all_data() -> None:
    t, channels = _synthetic_well()
    issue = _issue(t[0].timestamp() * 1000 - 100 * 3_600_000)  # 100h before any data
    assert build_precursors(issue, t, channels, []) is None


def test_build_precursors_window_covers_6h_before_the_event() -> None:
    t, channels = _synthetic_well()
    event_t = t[-1]
    issue = _issue(event_t.timestamp() * 1000)
    result = build_precursors(issue, t, channels, [])
    assert result is not None
    assert result["window_h"] == 6.0
    hkld = next(c for c in result["channels"] if c["channel"] == "HKLD")
    span_h = (hkld["t"][-1] - hkld["t"][0]) / 3_600_000.0
    assert 5.9 <= span_h <= 6.0


def test_build_precursors_band_is_null_without_matching_rigstate_samples() -> None:
    t, channels = _synthetic_well()
    issue = _issue(t[-1].timestamp() * 1000)
    result = build_precursors(issue, t, channels, [])  # no rigstate intervals at all
    assert result is not None
    for c in result["channels"]:
        assert c["band_lo"][0] is None
        assert c["band_hi"][0] is None


def test_build_precursors_band_uses_only_rotary_drilling_or_trip_within_50m_md() -> None:
    t, channels = _synthetic_well()
    # Make HKLD vary so a real P10-P90 band is computable, and mark the whole series as
    # rotary_drilling so the band mask matches (BITDEPTH is constant 2600, within tolerance).
    channels["HKLD"] = np.linspace(400.0, 600.0, len(t))
    intervals = [_interval(t[0], t[-1], "rotary_drilling")]
    issue = _issue(t[-1].timestamp() * 1000, md=2600.0)
    result = build_precursors(issue, t, channels, intervals)
    assert result is not None
    hkld = next(c for c in result["channels"] if c["channel"] == "HKLD")
    assert hkld["band_lo"][0] is not None
    assert hkld["band_lo"][0] < hkld["band_hi"][0]


def test_build_precursors_band_excludes_samples_outside_md_tolerance() -> None:
    t, channels = _synthetic_well()
    channels["HKLD"] = np.linspace(400.0, 600.0, len(t))
    channels["BITDEPTH"] = np.full(len(t), 5000.0)  # 2400 m away from the event's md
    intervals = [_interval(t[0], t[-1], "rotary_drilling")]
    issue = _issue(t[-1].timestamp() * 1000, md=2600.0)
    result = build_precursors(issue, t, channels, intervals)
    assert result is not None
    hkld = next(c for c in result["channels"] if c["channel"] == "HKLD")
    assert hkld["band_lo"][0] is None
