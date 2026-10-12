"""Composite best — docs/07_DATA_AND_ALGORITHMS.md §5: "P10 of durations / P90 of speeds, per
KPI per hole section per well; requires n ≥ 10, else falls back to well level and confidence drops
to low." (The confidence *level* itself is pipeline/strata_pipeline/confidence.py's job via its
C2 sample-size rule — this module just reports whether a section fell back, so the caller can
feed the right `n` into that rule.)"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .distributions import percentile

Kind = Literal["duration", "speed"]
_PCT_FOR_KIND: dict[Kind, float] = {"duration": 10.0, "speed": 90.0}


@dataclass(frozen=True)
class CompositeBestResult:
    value: float | None
    n: int  # the sample size actually used (section-level, or well-level on fallback)
    used_well_level_fallback: bool


def compute_composite_best(
    section_values: list[float],
    well_values: list[float],
    kind: Kind,
    min_n: int = 10,
) -> CompositeBestResult:
    pct = _PCT_FOR_KIND[kind]
    if len(section_values) >= min_n:
        return CompositeBestResult(
            value=percentile(section_values, pct), n=len(section_values), used_well_level_fallback=False
        )
    return CompositeBestResult(value=percentile(well_values, pct), n=len(well_values), used_well_level_fallback=True)


def compute_composite_best_by_section(
    values_by_section: dict[str, list[float]],
    kind: Kind,
    min_n: int = 10,
) -> dict[str, CompositeBestResult]:
    """Runs `compute_composite_best` for every section, using the union of all sections' values
    as that well's well-level fallback pool."""
    well_values = [v for values in values_by_section.values() for v in values]
    return {
        section: compute_composite_best(values, well_values, kind, min_n)
        for section, values in values_by_section.items()
    }
