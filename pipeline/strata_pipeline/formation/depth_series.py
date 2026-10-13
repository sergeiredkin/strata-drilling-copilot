"""Builds `DepthSeries` (`wells/<id>/depth_series.json`, `04_DATA_CONTRACTS.md` §3) — the
depth-indexed channels S6 (T11.3) plots alongside the formation tracks: ROP, MSE, dxc, gas,
MW_IN, ECD. Reuses the same MD bins `formation.depth_features.build_depth_features` already
computed for ROP/MSE/DXC/GAS; MW_IN/ECD aren't part of `DepthFeatureTable` (nothing else needs
them binned) so they're binned here directly via `bin_channel_by_depth`."""

from __future__ import annotations

from typing import Any

import numpy as np

from .depth_features import DepthFeatureTable, bin_channel_by_depth

_UNITS = {"ROP": "m/h", "MSE": "MPa", "DXC": "1", "GAS": "%", "MW_IN": "sg", "ECD": "sg"}


def _to_none_list(arr: np.ndarray) -> list[float | None]:
    return [None if not np.isfinite(v) else float(v) for v in arr]


def build_depth_series(
    well: str, channels: dict[str, np.ndarray], table: DepthFeatureTable, bin_size_m: float = 1.0
) -> dict[str, Any]:
    bit_md = channels.get("BITDEPTH")
    rop = channels.get("ROP")
    mw = (
        bin_channel_by_depth(bit_md, rop, channels.get("MW_IN"), bin_size_m)
        if bit_md is not None and rop is not None
        else None
    )
    ecd = (
        bin_channel_by_depth(bit_md, rop, channels.get("ECD"), bin_size_m)
        if bit_md is not None and rop is not None
        else None
    )
    n = len(table.md)

    def _series(values: np.ndarray | None) -> list[float | None]:
        return _to_none_list(values) if values is not None else [None] * n

    return {
        "well": well,
        "md": table.md.tolist(),
        "channels": {
            "ROP": {"unit": _UNITS["ROP"], "values": _series(table.rop_m_per_h)},
            "MSE": {"unit": _UNITS["MSE"], "values": _series(table.mse_mpa)},
            "DXC": {"unit": _UNITS["DXC"], "values": _series(table.dxc)},
            "GAS": {"unit": _UNITS["GAS"], "values": _series(table.gas_pct)},
            "MW_IN": {"unit": _UNITS["MW_IN"], "values": _series(mw)},
            "ECD": {"unit": _UNITS["ECD"], "values": _series(ecd)},
        },
    }


__all__ = ["build_depth_series"]
