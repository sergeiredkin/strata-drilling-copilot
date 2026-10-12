"""flat_time_pct / on_bottom_pct — docs/07_DATA_AND_ALGORITHMS.md §5. Both are fractions of
"total valid time" = every second NOT inside an R0 gap(`unknown`) interval — an R0 gap means the
classifier had no opinion at all, which must not silently count as flat/idle time."""

from __future__ import annotations

from strata_pipeline.rigstate.intervals import RigStateInterval

_FLAT_STATES = {"circulating", "reaming", "out_of_hole"}


def _duration(iv: RigStateInterval) -> float:
    return (iv.t1 - iv.t0).total_seconds()


def total_valid_seconds(intervals: list[RigStateInterval]) -> float:
    return sum(_duration(iv) for iv in intervals if iv.rule_id != "R0")


def flat_time_pct(intervals: list[RigStateInterval]) -> float | None:
    """circulating + reaming + unknown(R10, idle) + out_of_hole, over total valid time. None if
    there is no valid time at all (every sample was a gap)."""
    valid = total_valid_seconds(intervals)
    if valid <= 0:
        return None
    flat = sum(
        _duration(iv)
        for iv in intervals
        if iv.state in _FLAT_STATES or (iv.state == "unknown" and iv.rule_id == "R10")
    )
    return flat / valid


def on_bottom_pct(intervals: list[RigStateInterval]) -> float | None:
    """(rotary_drilling + sliding) over total valid time. None if there is no valid time."""
    valid = total_valid_seconds(intervals)
    if valid <= 0:
        return None
    on_bottom = sum(_duration(iv) for iv in intervals if iv.state in {"rotary_drilling", "sliding"})
    return on_bottom / valid
