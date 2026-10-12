from datetime import UTC, datetime, timedelta

from strata_pipeline.qc.align import align_well_channels
from strata_pipeline.qc.pipeline import ChannelQCResult

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _result(start_s: float, n: int, value: float) -> ChannelQCResult:
    t = [T0 + timedelta(seconds=start_s + i) for i in range(n)]
    return ChannelQCResult(channel="X", clean_t=t, clean_values=[value] * n, gaps=[], unit_fix=None)


def test_align_well_channels_spans_union_of_all_channel_ranges():
    channels = {
        "HKLD": _result(0, 10, 500.0),  # t = 0..9
        "RPM": _result(5, 10, 120.0),  # t = 5..14
    }
    t, aligned = align_well_channels(channels)
    assert t[0] == T0
    assert t[-1] == T0 + timedelta(seconds=14)
    assert len(t) == 15
    assert aligned["HKLD"][:10] == [500.0] * 10
    assert aligned["HKLD"][10:] == [None] * 5
    assert aligned["RPM"][:5] == [None] * 5
    assert aligned["RPM"][5:] == [120.0] * 10


def test_align_well_channels_empty_channel_stays_all_none():
    channels = {
        "HKLD": _result(0, 5, 500.0),
        "WOB": ChannelQCResult(channel="WOB", clean_t=[], clean_values=[], gaps=[], unit_fix=None),
    }
    t, aligned = align_well_channels(channels)
    assert len(t) == 5
    assert aligned["WOB"] == [None] * 5


def test_align_well_channels_all_empty_returns_empty():
    channels = {"HKLD": ChannelQCResult(channel="HKLD", clean_t=[], clean_values=[], gaps=[], unit_fix=None)}
    t, aligned = align_well_channels(channels)
    assert t == []
    assert aligned == {"HKLD": []}
