import math

import numpy as np
import pytest
from strata_pipeline.export.series import (
    LEVEL_BUCKET_S,
    export_channel_series,
    nan_run_gaps,
    read_strs,
    write_strs,
)


def test_write_read_roundtrip(tmp_path):
    mins = np.array([1.0, 2.0, np.nan, 4.0], dtype="f4")
    maxs = np.array([1.5, 2.5, np.nan, 4.5], dtype="f4")
    path = tmp_path / "chunk.bin"
    write_strs(path, t0_ms=1000.0, bucket_s=1.0, mins=mins, maxs=maxs)

    t0, bucket_s, out_min, out_max = read_strs(path)
    assert t0 == 1000.0
    assert bucket_s == 1.0
    np.testing.assert_allclose(out_min[:2], mins[:2])
    assert math.isnan(out_min[2])
    np.testing.assert_allclose(out_max[[0, 1, 3]], maxs[[0, 1, 3]])


def test_nan_run_gaps_detects_single_run():
    values = np.array([1.0, 1.0, np.nan, np.nan, np.nan, 1.0], dtype="f4")
    gaps = nan_run_gaps(t0_ms=0.0, bucket_s=1.0, values=values)
    assert gaps == [{"t0": 2000.0, "t1": 5000.0, "reason": "no_data"}]


def test_export_channel_series_preserves_spike_at_every_level(tmp_path):
    n = 8**3 * 4  # enough samples to reach L3 with margin
    rng = np.random.default_rng(0)
    values = rng.normal(0, 1, n).astype("f4")
    spike_i = n // 2
    values[spike_i] = 999.0  # single-sample spike; must survive min/max downsampling

    entry = export_channel_series(tmp_path, "HKLD", "kN", "synthetic", t0_ms=0.0, values=values)

    assert entry["unit"] == "kN"
    assert len(entry["levels"]) == len(LEVEL_BUCKET_S)

    for level_meta in entry["levels"]:
        level = level_meta["level"]
        bucket_s = level_meta["bucket_s"]
        spike_t = spike_i * 1000  # 1 Hz -> ms per sample
        found = False
        for chunk in level_meta["chunks"]:
            if not (chunk["t0"] <= spike_t < chunk["t1"]):
                continue
            _t0, _bs, mins, maxs = read_strs(tmp_path / chunk["file"])
            idx = int((spike_t - chunk["t0"]) / 1000 / bucket_s)
            assert maxs[idx] >= 999.0, f"spike lost at level {level}"
            found = True
        assert found, f"no chunk covers the spike at level {level}"


def test_export_channel_series_gap_listed(tmp_path):
    n = 100
    values = np.ones(n, dtype="f4")
    values[10:15] = np.nan
    entry = export_channel_series(tmp_path, "RPM", "rpm", "synthetic", t0_ms=0.0, values=values)
    assert entry["gaps"] == [{"t0": 10000.0, "t1": 15000.0, "reason": "no_data"}]


@pytest.mark.parametrize("level_idx", range(len(LEVEL_BUCKET_S)))
def test_level_bucket_sizes_are_8x(level_idx):
    if level_idx == 0:
        return
    assert LEVEL_BUCKET_S[level_idx] == LEVEL_BUCKET_S[level_idx - 1] * 8
