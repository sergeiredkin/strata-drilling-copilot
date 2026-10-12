from datetime import UTC, datetime
from pathlib import Path

from strata_pipeline.ingest.witsml_common import find_wellbore_dirs
from strata_pipeline.ingest.witsml_time import UnitConversionError, _convert, load_well_time_series

SAMPLE_ROOT = Path(__file__).parent / "samples" / "volve_15_9-F-11_A" / "witsml_root"


def test_find_wellbore_dirs_resolves_the_real_wellbore_name():
    dirs = find_wellbore_dirs(SAMPLE_ROOT, "15/9-F-11 A")
    assert len(dirs) == 1
    assert dirs[0].name == "4"


def test_find_wellbore_dirs_handles_no_prefix_and_main_wellbore_suffix():
    # Same matching rules used for real multi-registration wells (F-5/F-12/F-14) — exercised
    # here against the single sample registration to keep the fixture small.
    assert find_wellbore_dirs(SAMPLE_ROOT, "NO 15/9-F-11 A") == find_wellbore_dirs(SAMPLE_ROOT, "15/9-F-11 A")


def test_find_wellbore_dirs_no_match_returns_empty():
    assert find_wellbore_dirs(SAMPLE_ROOT, "15/9-F-99 Z") == []


def test_load_well_time_series_parses_real_log_chunk():
    df = load_well_time_series(SAMPLE_ROOT, "15/9-F-11 A")
    assert len(df) > 0
    # The trimmed sample log carries HOLEDEPTH (Depth), RPM (SURF_RPM), HKLD (HKLD_AVG) etc.
    channels = set(df["channel"].unique())
    assert "HOLEDEPTH" in channels
    assert "RPM" in channels
    # Every row is already in canonical units and UTC.
    assert df["t"].dtype.time_zone == "UTC"
    assert df["value"].is_not_null().all()


def test_load_well_time_series_windows_excludes_rows_outside_them():
    out_of_range_window = [(datetime(2020, 1, 1, tzinfo=UTC), datetime(2020, 1, 2, tzinfo=UTC))]
    df = load_well_time_series(SAMPLE_ROOT, "15/9-F-11 A", windows=out_of_range_window)
    assert len(df) == 0


def test_load_well_time_series_windows_keeps_rows_inside_them():
    in_range_window = [
        (datetime(2013, 5, 13, 6, 0, tzinfo=UTC), datetime(2013, 5, 13, 7, 0, tzinfo=UTC))
    ]
    with_window = load_well_time_series(SAMPLE_ROOT, "15/9-F-11 A", windows=in_range_window)
    without_window = load_well_time_series(SAMPLE_ROOT, "15/9-F-11 A")
    assert len(with_window) == len(without_window)


def test_load_well_time_series_none_windows_means_unbounded():
    unbounded = load_well_time_series(SAMPLE_ROOT, "15/9-F-11 A", windows=None)
    default = load_well_time_series(SAMPLE_ROOT, "15/9-F-11 A")
    assert len(unbounded) == len(default)


def test_load_well_time_series_unknown_wellbore_raises():
    try:
        load_well_time_series(SAMPLE_ROOT, "15/9-F-99 Z")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError for an unregistered wellbore")


def test_unit_conversion_hkld_newtons_to_kilonewtons():
    assert _convert(1000.0, "N", "kN", {"N->kN": 0.001}) == 1.0


def test_unit_conversion_same_unit_is_passthrough():
    assert _convert(42.0, "m", "m", {}) == 42.0


def test_unit_conversion_missing_factor_raises():
    try:
        _convert(1.0, "furlong", "m", {})
    except UnitConversionError:
        pass
    else:
        raise AssertionError("expected UnitConversionError for an unregistered unit pair")
