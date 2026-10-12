"""Unit detection & fix by plausible range — docs/07_DATA_AND_ALGORITHMS.md §3.1. This is a
safety net on top of ingest's declared-unit conversion (`ingest/mnemonics.yaml`): if a source
mislabels or omits a curve's unit, the ingested "canonical" value can still be wrong by a known
constant factor (e.g. hookload actually in lbf, declared as if already kN). Detected from the
channel's *median* (robust to a few bad samples) against `config.yaml`'s `unit_fix_rules`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UnitFixEvent:
    channel: str
    assumed_raw_unit: str
    factor: float
    median_before: float


def detect_and_fix_unit(
    values: list[float], channel: str, cfg: dict[str, Any]
) -> tuple[list[float], UnitFixEvent | None]:
    """Returns (possibly-corrected values, the fix event if one was applied). `values` must
    already exclude nulls/sentinels — the median is meaningless otherwise."""
    rule = cfg.get("unit_fix_rules", {}).get(channel)
    if rule is None or not values:
        return values, None
    median = _median(values)
    if median <= rule["median_above"]:
        return values, None
    factor_key = next(k for k in rule if k.startswith("factor_to_"))
    factor = rule[factor_key]
    fixed = [v * factor for v in values]
    event = UnitFixEvent(
        channel=channel,
        assumed_raw_unit=rule["assume_raw_unit"],
        factor=factor,
        median_before=median,
    )
    return fixed, event


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0
