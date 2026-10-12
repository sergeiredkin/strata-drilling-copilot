"""Per-well slips calibration — docs/07_DATA_AND_ALGORITHMS.md §4: "HL_slips = valley between the
two modes of the hookload histogram (fallback: travelling-block weight + 15%)." Recorded in
Evidence `params` by the caller — this module only computes the number."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlipsThreshold:
    hl_slips: float
    method: str  # "histogram_valley" | "travelling_block_fallback"


def compute_hl_slips(
    hkld_values: list[float | None],
    travelling_block_weight: float,
    fallback_margin: float,
    n_bins: int = 50,
) -> SlipsThreshold:
    """Builds a histogram of non-null `hkld_values` and looks for a valley (local minimum) between
    two modes (local maxima). Falls back to `travelling_block_weight * (1 + fallback_margin)` when
    the histogram doesn't have a clear two-mode shape (fewer than two local maxima, or no valley
    strictly between the two tallest ones)."""
    values = [v for v in hkld_values if v is not None]
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

    valley_idx = min(range(left_peak + 1, right_peak), key=lambda i: counts[i])
    hl_slips = lo + (valley_idx + 0.5) * width
    return SlipsThreshold(hl_slips=hl_slips, method="histogram_valley")


def _is_local_max(counts: list[int], i: int) -> bool:
    n = len(counts)
    left = counts[i - 1] if i > 0 else -1
    right = counts[i + 1] if i < n - 1 else -1
    return counts[i] > left and counts[i] > right
