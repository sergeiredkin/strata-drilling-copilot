import numpy as np
from strata_pipeline.formation.depth_features import DepthFeatureTable, bin_channels_by_depth
from strata_pipeline.formation.depth_series import build_depth_series


def _table_and_channels() -> tuple[DepthFeatureTable, dict[str, np.ndarray]]:
    n = 20
    channels = {
        "BITDEPTH": 1000.0 + np.arange(n, dtype="f8") * 0.5,  # 1000.0 .. 1009.5, 10 whole bins
        "ROP": np.full(n, 15.0),
        "GAS": np.full(n, 2.0),
        "MW_IN": np.full(n, 1.3),
        "ECD": np.full(n, 1.35),
    }
    table = bin_channels_by_depth([None] * n, channels, bin_size_m=1.0)
    assert table is not None
    return table, channels


def test_build_depth_series_shapes_every_channel_to_the_same_length_as_md() -> None:
    table, channels = _table_and_channels()
    series = build_depth_series("W1", channels, table)
    assert series["well"] == "W1"
    assert len(series["md"]) == 10
    for name in ("ROP", "MSE", "DXC", "GAS", "MW_IN", "ECD"):
        assert len(series["channels"][name]["values"]) == 10


def test_build_depth_series_bins_mw_and_ecd_from_the_raw_channels() -> None:
    table, channels = _table_and_channels()
    series = build_depth_series("W1", channels, table)
    assert series["channels"]["MW_IN"]["values"][0] == 1.3
    assert series["channels"]["ECD"]["values"][0] == 1.35
    assert series["channels"]["MW_IN"]["unit"] == "sg"


def test_build_depth_series_nan_becomes_null_not_fabricated() -> None:
    table, channels = _table_and_channels()
    table.dxc[:] = np.nan  # e.g. no ECD ingested at all for this well (a real case, see T11.1)
    series = build_depth_series("W1", channels, table)
    assert all(v is None for v in series["channels"]["DXC"]["values"])


def test_build_depth_series_without_bitdepth_leaves_mw_ecd_null() -> None:
    table, channels = _table_and_channels()
    del channels["BITDEPTH"]
    series = build_depth_series("W1", channels, table)
    assert all(v is None for v in series["channels"]["MW_IN"]["values"])
    assert all(v is None for v in series["channels"]["ECD"]["values"])
