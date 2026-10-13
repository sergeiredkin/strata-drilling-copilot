from datetime import UTC, datetime, timedelta

import numpy as np
from strata_pipeline.qc.align import align_well_channels
from strata_pipeline.qc.pipeline import ChannelQCResult

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _result(start_s: float, n: int, value: float) -> ChannelQCResult:
    return ChannelQCResult(
        channel="X",
        clean_t0=T0 + timedelta(seconds=start_s),
        clean_values=np.full(n, value, dtype=np.float64),
        gaps=[],
        unit_fix=None,
    )


def _empty_result(channel: str) -> ChannelQCResult:
    return ChannelQCResult(
        channel=channel, clean_t0=None, clean_values=np.array([], dtype=np.float64), gaps=[], unit_fix=None
    )


def test_align_well_channels_spans_union_of_all_channel_ranges():
    channels = {
        "HKLD": _result(0, 10, 500.0),  # t = 0..9
        "RPM": _result(5, 10, 120.0),  # t = 5..14
    }
    t, aligned = align_well_channels(channels)
    assert t[0] == T0
    assert t[-1] == T0 + timedelta(seconds=14)
    assert len(t) == 15
    assert aligned["HKLD"][:10].tolist() == [500.0] * 10
    assert np.isnan(aligned["HKLD"][10:]).all()
    assert np.isnan(aligned["RPM"][:5]).all()
    assert aligned["RPM"][5:].tolist() == [120.0] * 10


def test_align_well_channels_empty_channel_stays_all_none():
    channels = {
        "HKLD": _result(0, 5, 500.0),
        "WOB": _empty_result("WOB"),
    }
    t, aligned = align_well_channels(channels)
    assert len(t) == 5
    assert np.isnan(aligned["WOB"]).all()


def test_align_well_channels_all_empty_returns_empty():
    channels = {"HKLD": _empty_result("HKLD")}
    t, aligned = align_well_channels(channels)
    assert t == []
    assert aligned["HKLD"].tolist() == []
