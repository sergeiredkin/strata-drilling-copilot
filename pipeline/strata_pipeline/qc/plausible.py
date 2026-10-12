"""Plausible-range filtering — docs/07_DATA_AND_ALGORITHMS.md §3.1 defines per-channel ranges
(`config.yaml`'s `qc.plausible_ranges`) for the unit-fix heuristic, but a value can be wildly
implausible in its own, correctly-identified unit too (a stuck-bit, cosmic-ray, or decoding
glitch in the raw file) — found against real data: ~0.02% of one well's real HKLD samples were
outside [0, 4000] kN (down to -35504, up to +519337), too rare to be a sustained "real excursion"
Hampel's single-sample-only rule would catch, but extreme enough to blow out any downstream
statistic computed over the raw min..max range (histogram binning, in particular). Flagged the
same way as a sentinel: removed, reasoned, never silently kept."""

from __future__ import annotations


def implausible_mask(values: list[float | None], plausible_min: float, plausible_max: float) -> list[bool]:
    return [v is not None and (v < plausible_min or v > plausible_max) for v in values]
