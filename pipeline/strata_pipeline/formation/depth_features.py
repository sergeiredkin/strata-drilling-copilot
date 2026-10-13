"""T11.1 depth-indexed export — docs/07_DATA_AND_ALGORITHMS.md §9/§11: resample the already
time-aligned, 1 Hz channels (qc.align.align_well_channels's output) onto 1 m MD bins, keyed by
BITDEPTH, and compute the physics features T11.2's classifier trains on: ROP, MSE (Teale),
surface torque, WOB, RPM, dxc (Jorden & Shirley, ECD-corrected), total gas, plus rolling mean/std
over 5 and 20 m.

Bit diameter (needed for MSE's bit area and dxc's `12W/(1e6*D)` term) is the same number as the
hole size the bit is cutting — not read from any BHA/bit-run-specific file (there is none in the
downloaded Volve archives) but from the DDR `<bitRecord><diaBit>` field alongside each bit run's
`mdHoleStart`/`mdHoleStop` (`ingest/ddr.py:load_well_bit_runs`), matched to whichever MD bin falls
inside that run's range (ADR 0010). `BitInterval`/`bit_diameter_by_md` do that lookup; a bin
outside every reported run's range gets NaN, never a guessed diameter."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np

_FT_PER_M = 3.28084
_LBF_PER_KN = 224.809  # kN -> klbf (0.224809) -> lbf (x1000)
_SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class BitInterval:
    """One reported bit run (`ingest/ddr.py`'s `diaBit`/`mdHoleStart`/`mdHoleStop`). `md_base` is
    exclusive, matching `bit_diameter_by_md`'s `[md_top, md_base)` lookup."""

    md_top: float
    md_base: float
    diameter_in: float


def bit_diameter_by_md(md: np.ndarray, intervals: Sequence[BitInterval]) -> np.ndarray:
    """Looks up each MD bin's bit diameter from reported bit-run intervals. NaN where no interval
    covers that depth. Intervals are applied in the order given — pass them in chronological
    (DDR file) order so a later report's revision of an earlier run's range wins the overlap,
    rather than the reverse."""
    out = np.full(len(md), np.nan)
    for iv in intervals:
        out[(md >= iv.md_top) & (md < iv.md_base)] = iv.diameter_in
    return out


@dataclass(frozen=True)
class DepthFeatureTable:
    """One row per populated 1 m MD bin. `md` is the bin's lower edge. Every feature array is
    NaN where that bin has no qualifying samples (gaps are never interpolated — docs/01 rule)."""

    md: np.ndarray
    rop_m_per_h: np.ndarray
    wob_kN: np.ndarray
    rpm: np.ndarray
    torque_kNm: np.ndarray
    gas_pct: np.ndarray
    mse_mpa: np.ndarray
    dxc: np.ndarray
    n_samples: np.ndarray  # samples aggregated into each bin — T11.2's per-bin confidence input


def _depth_bin_index(bit_md: np.ndarray, bin_size_m: float) -> tuple[np.ndarray, int, int]:
    bin_idx = np.floor(bit_md / bin_size_m).astype(np.int64)
    return bin_idx, int(np.min(bin_idx)), int(np.max(bin_idx))


def _bin_mean(values: np.ndarray, bin_idx: np.ndarray, lo: int, n_bins: int) -> np.ndarray:
    out = np.full(n_bins, np.nan, dtype=np.float64)
    valid = np.isfinite(values)
    if not np.any(valid):
        return out
    sums = np.bincount(bin_idx[valid] - lo, weights=values[valid], minlength=n_bins)
    counts = np.bincount(bin_idx[valid] - lo, minlength=n_bins)
    nonzero = counts > 0
    out[nonzero] = sums[nonzero] / counts[nonzero]
    return out


def bin_channel_by_depth(
    bit_md: np.ndarray, rop: np.ndarray, values: np.ndarray | None, bin_size_m: float = 1.0
) -> np.ndarray | None:
    """Mean-aggregates one channel's samples into `bin_size_m` MD bins keyed by `bit_md`,
    restricted to samples where the bit is advancing (`rop > 0` — see `bin_channels_by_depth`).
    Returns None if there's no qualifying sample at all (distinct from an all-NaN array, which
    means bins exist but this particular channel is missing)."""
    drilling = np.isfinite(bit_md) & np.isfinite(rop) & (rop > 0)
    if not np.any(drilling) or values is None:
        return None
    bin_idx, lo, hi = _depth_bin_index(bit_md[drilling], bin_size_m)
    n_bins = hi - lo + 1
    return _bin_mean(values[drilling], bin_idx, lo, n_bins)


def bin_channels_by_depth(
    t: list[datetime],
    channels: dict[str, np.ndarray],
    bin_size_m: float = 1.0,
) -> DepthFeatureTable | None:
    """Groups 1 Hz samples by their BITDEPTH into `bin_size_m` MD bins and mean-aggregates ROP,
    WOB, RPM, TORQ, GAS within each bin. Only samples with ROP > 0 count (ROP == 0 means the bit
    isn't advancing — not drilling that depth — and would make MSE/dxc divide by zero below).
    Returns None if there's no BITDEPTH or no qualifying sample at all."""
    bit_md = channels.get("BITDEPTH")
    rop = channels.get("ROP")
    if bit_md is None or rop is None or len(t) == 0:
        return None

    drilling = np.isfinite(bit_md) & np.isfinite(rop) & (rop > 0)
    if not np.any(drilling):
        return None

    bin_idx, lo, hi = _depth_bin_index(bit_md[drilling], bin_size_m)
    n_bins = hi - lo + 1
    md = np.arange(lo, hi + 1, dtype=np.float64) * bin_size_m

    def _feature(name: str) -> np.ndarray:
        arr = channels.get(name)
        if arr is None:
            return np.full(n_bins, np.nan)
        return _bin_mean(arr[drilling], bin_idx, lo, n_bins)

    n_samples = np.bincount(bin_idx - lo, minlength=n_bins).astype(np.float64)

    return DepthFeatureTable(
        md=md,
        rop_m_per_h=_feature("ROP"),
        wob_kN=_feature("WOB"),
        rpm=_feature("RPM"),
        torque_kNm=_feature("TORQ"),
        gas_pct=_feature("GAS"),
        mse_mpa=np.full(n_bins, np.nan),
        dxc=np.full(n_bins, np.nan),
        n_samples=n_samples,
    )


def compute_mse(
    wob_kN: np.ndarray,
    torque_kNm: np.ndarray,
    rpm: np.ndarray,
    rop_m_per_h: np.ndarray,
    bit_diameter_in: np.ndarray,
) -> np.ndarray:
    """Teale MSE, SI in -> MPa out (07 §11): `WOB/A + 2*pi*N*T / (A*ROP)`, surface torque used for
    T (a stated limitation, not a downhole measurement). `bit_diameter_in` is per-bin (see
    `bit_diameter_by_md`); NaN wherever any input is non-finite, ROP is 0, or the diameter at
    that bin is unknown."""
    diameter_m = bit_diameter_in * 0.0254
    area_m2 = np.pi * (diameter_m / 2.0) ** 2

    wob_n = wob_kN * 1000.0
    torque_nm = torque_kNm * 1000.0
    n_rps = rpm / 60.0
    rop_mps = rop_m_per_h / _SECONDS_PER_HOUR

    with np.errstate(divide="ignore", invalid="ignore"):
        mse_pa = wob_n / area_m2 + (2.0 * np.pi * n_rps * torque_nm) / (area_m2 * rop_mps)
    mse_pa[~np.isfinite(mse_pa)] = np.nan
    mse_pa[rop_mps <= 0] = np.nan
    return mse_pa / 1.0e6


def compute_dxc(
    rop_m_per_h: np.ndarray,
    rpm: np.ndarray,
    wob_kN: np.ndarray,
    bit_diameter_in: np.ndarray,
    ecd_sg: np.ndarray | None,
    rho_normal_sg: float = 1.03,
) -> np.ndarray:
    """Corrected d-exponent, Jorden & Shirley (07 §11): `d = log10(R/(60N)) / log10(12W/(1e6*D))`
    (R ft/h, N rpm, W lbf, D in) then `dxc = d * (rho_normal/ECD)`. `bit_diameter_in` is per-bin
    (see `bit_diameter_by_md`); NaN wherever an input is non-finite/non-positive (log of a
    non-positive argument), the diameter at that bin is unknown, or (for the ECD correction) ECD
    itself isn't available — the uncorrected `d` is never silently substituted for `dxc`, since
    that would misrepresent an uncorrected number as the corrected one."""
    n = len(rop_m_per_h)
    rop_ft_per_h = rop_m_per_h * _FT_PER_M
    wob_lbf = wob_kN * _LBF_PER_KN

    with np.errstate(divide="ignore", invalid="ignore"):
        numerator = rop_ft_per_h / (60.0 * rpm)
        denominator = (12.0 * wob_lbf) / (1.0e6 * bit_diameter_in)
        d = np.log10(numerator) / np.log10(denominator)
    d[~np.isfinite(d)] = np.nan
    d[(numerator <= 0) | (denominator <= 0)] = np.nan

    if ecd_sg is None:
        return np.full(n, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        dxc = d * (rho_normal_sg / ecd_sg)
    dxc[~np.isfinite(dxc)] = np.nan
    return dxc


def rolling_mean_std(values: np.ndarray, window_bins: int) -> tuple[np.ndarray, np.ndarray]:
    """Centred rolling mean/std over `window_bins` consecutive MD bins (bins are fixed-width, so
    a bin count is also a metre count at `bin_size_m=1`). NaN bins are excluded from each window,
    not treated as zero; a window with zero finite values yields NaN (never interpolated)."""
    n = len(values)
    half = window_bins // 2
    mean = np.full(n, np.nan)
    std = np.full(n, np.nan)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        window = values[lo:hi]
        finite = window[np.isfinite(window)]
        if finite.size > 0:
            mean[i] = finite.mean()
            std[i] = finite.std()
    return mean, std


def build_depth_features(
    t: list[datetime],
    channels: dict[str, np.ndarray],
    bit_intervals: Sequence[BitInterval] | None = None,
    rho_normal_sg: float = 1.03,
    bin_size_m: float = 1.0,
    rolling_windows_m: tuple[int, ...] = (5, 20),
) -> DepthFeatureTable | None:
    """Orchestrates binning + MSE/dxc for one well. `bit_intervals` resolves each bin's bit
    diameter via `bit_diameter_by_md` (no intervals -> every bin's diameter is unknown, so MSE/
    dxc come back all-NaN). Rolling mean/std (07 §9) are intentionally not part of
    `DepthFeatureTable` — T11.2 computes them per-feature as needed via `rolling_mean_std`, since
    which features get rolled is a model-input decision, not an export shape."""
    table = bin_channels_by_depth(t, channels, bin_size_m)
    if table is None:
        return None
    bit_md = channels.get("BITDEPTH")
    rop = channels.get("ROP")
    ecd_binned = (
        bin_channel_by_depth(bit_md, rop, channels.get("ECD"), bin_size_m)
        if bit_md is not None and rop is not None
        else None
    )

    bit_diameter_in = bit_diameter_by_md(table.md, bit_intervals or [])
    mse = compute_mse(table.wob_kN, table.torque_kNm, table.rpm, table.rop_m_per_h, bit_diameter_in)
    dxc = compute_dxc(table.rop_m_per_h, table.rpm, table.wob_kN, bit_diameter_in, ecd_binned, rho_normal_sg)
    return DepthFeatureTable(
        md=table.md,
        rop_m_per_h=table.rop_m_per_h,
        wob_kN=table.wob_kN,
        rpm=table.rpm,
        torque_kNm=table.torque_kNm,
        gas_pct=table.gas_pct,
        mse_mpa=mse,
        dxc=dxc,
        n_samples=table.n_samples,
    )


__all__ = [
    "BitInterval",
    "DepthFeatureTable",
    "bin_channel_by_depth",
    "bin_channels_by_depth",
    "bit_diameter_by_md",
    "build_depth_features",
    "compute_dxc",
    "compute_mse",
    "rolling_mean_std",
]
