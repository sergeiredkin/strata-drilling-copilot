"""Generic distribution statistics — docs/07_DATA_AND_ALGORITHMS.md §5: "Distributions report
min, q1, median, q3, max, outliers (> q3 + 1.5 IQR) with their windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Sample(Generic[T]):
    value: float
    window: T  # caller-defined window identifier (e.g. a (t0, t1) pair) kept only for outliers


@dataclass(frozen=True)
class Outlier(Generic[T]):
    value: float
    window: T


@dataclass(frozen=True)
class Distribution(Generic[T]):
    n: int
    min: float
    q1: float
    median: float
    q3: float
    max: float
    outliers: list[Outlier[T]]


def compute_distribution(samples: list[Sample[T]]) -> Distribution[T] | None:
    """None if there are no samples at all — never fabricate a zero-sample distribution."""
    if not samples:
        return None
    values = sorted(s.value for s in samples)
    q1 = _percentile(values, 25.0)
    median = _percentile(values, 50.0)
    q3 = _percentile(values, 75.0)
    iqr = q3 - q1
    threshold = q3 + 1.5 * iqr
    outliers = [Outlier(value=s.value, window=s.window) for s in samples if s.value > threshold]
    return Distribution(
        n=len(samples),
        min=values[0],
        q1=q1,
        median=median,
        q3=q3,
        max=values[-1],
        outliers=outliers,
    )


def percentile(values: list[float], pct: float) -> float | None:
    """Standalone percentile for composite-best (P10 of durations, P90 of speeds) — same
    linear-interpolation method `compute_distribution` uses internally, exposed directly since
    composite-best needs a single percentile, not the full five-number summary."""
    if not values:
        return None
    return _percentile(sorted(values), pct)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear interpolation between closest ranks (the common "R-7"/numpy-default method)."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac
