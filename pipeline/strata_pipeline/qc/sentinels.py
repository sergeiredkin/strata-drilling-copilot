"""Sentinel detection — docs/07_DATA_AND_ALGORITHMS.md §3.2: known fill values (-999.25, -9999,
9999) are not real readings and must become a gap(`sentinel`), never a plotted value."""

from __future__ import annotations

import polars as pl

_TOL = 1e-6


def sentinel_mask(values: pl.Series, sentinels: list[float]) -> pl.Series:
    """True where `values` equals one of `sentinels` (within float tolerance) or is NaN."""
    mask = values.is_nan().fill_null(False)
    for s in sentinels:
        mask = mask | (values - s).abs().lt(_TOL).fill_null(False)
    return mask
