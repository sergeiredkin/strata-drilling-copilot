"""Per-well slips calibration — docs/07_DATA_AND_ALGORITHMS.md §4: "HL_slips = valley between the
two modes of the hookload histogram (fallback: travelling-block weight + 15%)." Recorded in
Evidence `params` by the caller — this module only computes the number."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SlipsThreshold:
    hl_slips: float
    method: str  # "histogram_valley" | "travelling_block_fallback"


def compute_hl_slips(
    hkld_values: np.ndarray,
    travelling_block_weight: float,
    fallback_margin: float,
    n_bins: int = 50,
    min_peak_frac: float = 0.05,
    min_valley_drop_frac: float = 0.5,
) -> SlipsThreshold:
    """Builds a histogram of non-NaN `hkld_values` and looks for a valley (local minimum) between
    two modes (local maxima). Falls back to `travelling_block_weight * (1 + fallback_margin)` when
    the histogram doesn't have a clear two-mode shape: fewer than two local maxima, no valley
    strictly between the two tallest ones, either peak holding less than `min_peak_frac` of all
    samples (a real second population, not one noisy bin), or the valley not dipping below
    `min_valley_drop_frac` of the *smaller* peak's height (otherwise a continuous, roughly
    unimodal distribution's own sampling noise gets misread as two modes — this matters for a
    well that's genuinely all-drilling with no real slips population in the window at all).
    `hkld_values` is filtered with a vectorized NaN mask, not a Python list comprehension, since
    on a multi-year-gap real well it can be tens of millions of samples long with only a small
    fraction surviving QC/gridding."""
    values = hkld_values[~np.isnan(hkld_values)].tolist()
    fallback = SlipsThreshold(
        hl_slips=travelling_block_weight * (1.0 + fallback_margin),
        method="travelling_block_fallback",
    )
    if len(values) < n_bins:
        return fallback

    lo, hi = min(values), max(values)
    if hi <= lo:
        return fallback
    width = (hi - lo) / n_bins
    counts = [0] * n_bins
    for v in values:
        idx = min(n_bins - 1, int((v - lo) / width))
        counts[idx] += 1

    peaks = [i for i in range(n_bins) if _is_local_max(counts, i)]
    if len(peaks) < 2:
        return fallback
    peaks_by_height = sorted(peaks, key=lambda i: counts[i], reverse=True)
    left_peak, right_peak = sorted(peaks_by_height[:2])
    if right_peak <= left_peak + 1:
        return fallback

    min_peak_count = min_peak_frac * len(values)
    if counts[left_peak] < min_peak_count or counts[right_peak] < min_peak_count:
        return fallback

    valley_idx = min(range(left_peak + 1, right_peak), key=lambda i: counts[i])
    smaller_peak_count = min(counts[left_peak], counts[right_peak])
    if counts[valley_idx] > min_valley_drop_frac * smaller_peak_count:
        return fallback

    hl_slips = lo + (valley_idx + 0.5) * width
    return SlipsThreshold(hl_slips=hl_slips, method="histogram_valley")


def _is_local_max(counts: list[int], i: int) -> bool:
    n = len(counts)
    left = counts[i - 1] if i > 0 else -1
    right = counts[i + 1] if i < n - 1 else -1
    return counts[i] > left and counts[i] > right
