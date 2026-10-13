from datetime import UTC, datetime, timedelta

import numpy as np
from strata_pipeline.formation.depth_features import (
    BitInterval,
    bin_channel_by_depth,
    bin_channels_by_depth,
    bit_diameter_by_md,
    build_depth_features,
    compute_dxc,
    compute_mse,
    rolling_mean_std,
)


def _synthetic_well(n: int = 40) -> tuple[list[datetime], dict[str, np.ndarray]]:
    t0 = datetime(2020, 1, 1, tzinfo=UTC)
    t = [t0 + timedelta(seconds=i) for i in range(n)]
    channels = {
        "BITDEPTH": np.arange(n, dtype="f8") * 0.5 + 1000.0,  # 1000.0 .. 1019.5, 0.5 m/sample
        "ROP": np.full(n, 18.0),  # m/h, constant and > 0
        "WOB": np.full(n, 50.0),  # kN
        "RPM": np.full(n, 120.0),
        "TORQ": np.full(n, 20.0),  # kN.m
        "GAS": np.full(n, 2.0),  # %
        "ECD": np.full(n, 1.1),  # sg
    }
    return t, channels


def test_bin_channels_by_depth_aggregates_1m_bins() -> None:
    t, channels = _synthetic_well()
    table = bin_channels_by_depth(t, channels, bin_size_m=1.0)
    assert table is not None
    assert table.md[0] == 1000.0
    assert table.md[-1] == 1019.0
    np.testing.assert_allclose(table.rop_m_per_h, 18.0)
    np.testing.assert_allclose(table.wob_kN, 50.0)
    np.testing.assert_allclose(table.gas_pct, 2.0)
    # 0.5 m/sample -> 2 samples per 1 m bin, except possibly the last partial bin.
    assert table.n_samples[0] == 2


def test_bin_channels_by_depth_excludes_non_drilling_samples() -> None:
    t, channels = _synthetic_well()
    channels["ROP"][:10] = 0.0  # not advancing -- must not count toward any bin
    table = bin_channels_by_depth(t, channels, bin_size_m=1.0)
    assert table is not None
    assert table.n_samples.sum() == 30


def test_bin_channels_by_depth_returns_none_without_bitdepth_or_rop() -> None:
    t, channels = _synthetic_well()
    del channels["BITDEPTH"]
    assert bin_channels_by_depth(t, channels) is None


def test_bin_channel_by_depth_matches_fixed_feature() -> None:
    _t, channels = _synthetic_well()
    out = bin_channel_by_depth(channels["BITDEPTH"], channels["ROP"], channels["GAS"], bin_size_m=1.0)
    assert out is not None
    np.testing.assert_allclose(out, 2.0)


def test_compute_mse_is_finite_and_positive_with_known_bit_diameter() -> None:
    wob = np.array([50.0, 50.0])
    torque = np.array([20.0, 20.0])
    rpm = np.array([120.0, 120.0])
    rop = np.array([18.0, 18.0])
    mse = compute_mse(wob, torque, rpm, rop, bit_diameter_in=np.array([8.5, 8.5]))
    assert np.all(np.isfinite(mse))
    assert np.all(mse > 0)


def test_compute_mse_is_nan_without_bit_diameter() -> None:
    wob = np.array([50.0])
    mse = compute_mse(wob, wob, wob, wob + 1, bit_diameter_in=np.array([np.nan]))
    assert np.isnan(mse).all()


def test_compute_mse_is_nan_at_zero_rop() -> None:
    wob = np.array([50.0])
    mse = compute_mse(wob, wob, np.array([120.0]), np.array([0.0]), bit_diameter_in=np.array([8.5]))
    assert np.isnan(mse).all()


def test_compute_dxc_requires_both_bit_diameter_and_ecd() -> None:
    rop = np.array([18.0])
    rpm = np.array([120.0])
    wob = np.array([50.0])
    ecd = np.array([1.1])
    assert np.isnan(compute_dxc(rop, rpm, wob, np.array([np.nan]), ecd)).all()
    assert np.isnan(compute_dxc(rop, rpm, wob, np.array([8.5]), None)).all()
    dxc = compute_dxc(rop, rpm, wob, np.array([8.5]), ecd)
    assert np.isfinite(dxc).all()


def test_bit_diameter_by_md_looks_up_the_covering_interval() -> None:
    md = np.array([999.0, 1000.0, 1005.5, 2000.0])
    intervals = [BitInterval(md_top=1000.0, md_base=2000.0, diameter_in=8.5)]
    out = bit_diameter_by_md(md, intervals)
    assert np.isnan(out[0])  # below every interval
    assert out[1] == 8.5
    assert out[2] == 8.5
    assert np.isnan(out[3])  # md_base is exclusive


def test_bit_diameter_by_md_later_interval_wins_an_overlap() -> None:
    # Mirrors the real F-11 A DDR: a later report revising an earlier run's range.
    md = np.array([1500.0])
    intervals = [
        BitInterval(md_top=1000.0, md_base=2000.0, diameter_in=12.25),
        BitInterval(md_top=1400.0, md_base=1600.0, diameter_in=8.5),
    ]
    assert bit_diameter_by_md(md, intervals)[0] == 8.5


def test_rolling_mean_std_excludes_nan_bins() -> None:
    values = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    mean, std = rolling_mean_std(values, window_bins=3)
    assert mean[2] == (2.0 + 4.0) / 2  # centred window [1,2,3] with index 2 (nan) excluded
    assert not np.isnan(std[2])


def test_build_depth_features_without_bit_intervals_leaves_mse_dxc_null() -> None:
    t, channels = _synthetic_well()
    table = build_depth_features(t, channels, bit_intervals=None)
    assert table is not None
    assert np.isnan(table.mse_mpa).all()
    assert np.isnan(table.dxc).all()
    np.testing.assert_allclose(table.rop_m_per_h, 18.0)


def test_build_depth_features_with_bit_intervals_computes_mse_and_dxc() -> None:
    t, channels = _synthetic_well()
    intervals = [BitInterval(md_top=1000.0, md_base=1020.0, diameter_in=8.5)]
    table = build_depth_features(t, channels, bit_intervals=intervals)
    assert table is not None
    assert np.isfinite(table.mse_mpa).all()
    assert np.isfinite(table.dxc).all()


def test_build_depth_features_partial_bit_coverage_leaves_the_rest_null() -> None:
    t, channels = _synthetic_well()
    # Only covers the first half of the bin range -- the second half must stay null, not
    # fall back to the first interval's diameter.
    intervals = [BitInterval(md_top=1000.0, md_base=1010.0, diameter_in=8.5)]
    table = build_depth_features(t, channels, bit_intervals=intervals)
    assert table is not None
    assert np.isfinite(table.mse_mpa[:10]).all()
    assert np.isnan(table.mse_mpa[10:]).all()
