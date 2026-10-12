"""QC score — docs/07_DATA_AND_ALGORITHMS.md §3.6:
score = coverage_weighted × (1 − core_gap_fraction) × survived_fraction."""

from __future__ import annotations

from typing import Literal

CoverageLevel = Literal["full", "partial", "none"]
_LEVEL_VALUE: dict[CoverageLevel, float] = {"full": 1.0, "partial": 0.5, "none": 0.0}


def coverage_weighted_score(coverage: dict[str, CoverageLevel], weights: dict[str, float]) -> float:
    """`coverage` maps a source name (e.g. "time_logs", "survey") to full/partial/none; `weights`
    is `config.yaml`'s `qc.coverage_weights`. Sources missing from `coverage` are treated as
    "none" — never assumed present."""
    return sum(weights[source] * _LEVEL_VALUE[coverage.get(source, "none")] for source in weights)


def qc_score(
    coverage: dict[str, CoverageLevel],
    weights: dict[str, float],
    core_gap_fraction: float,
    survived_fraction: float,
) -> float:
    cw = coverage_weighted_score(coverage, weights)
    return cw * (1.0 - core_gap_fraction) * survived_fraction
