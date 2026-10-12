from datetime import UTC, datetime, timedelta

import polars as pl
from strata_pipeline.ingest.drilling_window import drilling_windows_from_ddr, in_any_window

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _ddr_df(rows: list[tuple[float, float, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "t0": [T0 + timedelta(hours=t0) for t0, _, _ in rows],
            "t1": [T0 + timedelta(hours=t1) for _, t1, _ in rows],
            "normalized_code": [code for _, _, code in rows],
        }
    )


def test_drilling_windows_from_ddr_merges_rows_within_gap_threshold():
    df = _ddr_df([(0, 2, "DRILL"), (3, 5, "TRIP"), (10, 12, "CIRC")])
    windows = drilling_windows_from_ddr(df, merge_gap_hours=5.0)
    assert windows == [(T0, T0 + timedelta(hours=12))]


def test_drilling_windows_from_ddr_splits_on_large_gap():
    df = _ddr_df([(0, 2, "DRILL"), (1000, 1002, "DRILL")])
    windows = drilling_windows_from_ddr(df, merge_gap_hours=500.0)
    assert len(windows) == 2
    assert windows[0] == (T0, T0 + timedelta(hours=2))
    assert windows[1] == (T0 + timedelta(hours=1000), T0 + timedelta(hours=1002))


def test_drilling_windows_from_ddr_ignores_non_drilling_codes():
    df = _ddr_df([(0, 2, "WAIT"), (3, 5, "OTHER")])
    assert drilling_windows_from_ddr(df) == []


def test_drilling_windows_from_ddr_empty_input_returns_empty():
    df = _ddr_df([])
    assert drilling_windows_from_ddr(df) == []


def test_in_any_window_true_inside_false_outside():
    windows = [(T0, T0 + timedelta(hours=2)), (T0 + timedelta(hours=10), T0 + timedelta(hours=12))]
    assert in_any_window(T0 + timedelta(hours=1), windows) is True
    assert in_any_window(T0 + timedelta(hours=11), windows) is True
    assert in_any_window(T0 + timedelta(hours=5), windows) is False


def test_in_any_window_empty_windows_list_is_always_false():
    assert in_any_window(T0, []) is False
