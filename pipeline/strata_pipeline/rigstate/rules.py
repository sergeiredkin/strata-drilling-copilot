"""Rig-state rules — docs/07_DATA_AND_ALGORITHMS.md §4, first match wins, `rule_id` stored for
every sample so a reviewer can see exactly which rule decided it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .flags import Flags

CORE_CHANNELS = ["HKLD", "BPOS", "FLOWIN", "RPM", "BITDEPTH", "HOLEDEPTH"]

STATES = (
    "unknown",
    "out_of_hole",
    "connection",
    "trip_in",
    "trip_out",
    "rotary_drilling",
    "sliding",
    "reaming",
    "circulating",
)


@dataclass(frozen=True)
class Decision:
    value: float
    threshold: float


@dataclass(frozen=True)
class RuleResult:
    state: str
    rule_id: str
    deciding: list[Decision] = field(default_factory=list)
    back_reaming: bool = False


def classify_sample(
    raw: dict[str, float | None],
    flags: Flags,
    trip_direction: str | None,
    hl_slips: float,
    cfg: dict[str, Any],
) -> RuleResult:
    """`raw` must have every key in CORE_CHANNELS. `trip_direction` is "trip_in"/"trip_out"/None,
    the sign of the net BITDEPTH change over the trailing calibration window — used only by R3,
    where `moving`/`v` are near zero (the pipe is in slips, not actually travelling)."""
    if any(raw[c] is None for c in CORE_CHANNELS):
        return RuleResult("unknown", "R0")

    bitdepth = raw["BITDEPTH"]
    assert bitdepth is not None  # narrowed by the R0 check above
    flowin = raw["FLOWIN"]
    assert flowin is not None
    hkld = raw["HKLD"]
    assert hkld is not None
    rpm = raw["RPM"]
    assert rpm is not None

    if bitdepth < cfg["out_of_hole_bitdepth_m"] and not flags.pumping:
        return RuleResult(
            "out_of_hole",
            "R1",
            [Decision(bitdepth, cfg["out_of_hole_bitdepth_m"]), Decision(flowin, cfg["pumping_lpm"])],
        )

    margin = flags.holedepth_minus_bitdepth
    assert margin is not None  # core channels all present here

    if flags.in_slips and flags.near_bottom:
        return RuleResult(
            "connection",
            "R2",
            [Decision(hkld, hl_slips), Decision(margin, cfg["near_bottom_m"])],
        )

    if flags.in_slips and not flags.near_bottom:
        state = trip_direction if trip_direction in ("trip_in", "trip_out") else "trip_out"
        return RuleResult(
            state,
            "R3",
            [Decision(hkld, hl_slips), Decision(margin, cfg["near_bottom_m"])],
        )

    if flags.on_bottom and flags.pumping and flags.rotating:
        return RuleResult(
            "rotary_drilling",
            "R4",
            [
                Decision(margin, cfg["on_bottom_m"]),
                Decision(flowin, cfg["pumping_lpm"]),
                Decision(rpm, cfg["rotating_rpm"]),
            ],
        )

    if flags.on_bottom and flags.pumping and not flags.rotating:
        return RuleResult(
            "sliding",
            "R5",
            [
                Decision(margin, cfg["on_bottom_m"]),
                Decision(flowin, cfg["pumping_lpm"]),
                Decision(rpm, cfg["rotating_rpm"]),
            ],
        )

    if not flags.on_bottom and flags.pumping and flags.rotating and flags.moving:
        v = flags.v
        assert v is not None
        return RuleResult(
            "reaming",
            "R6",
            [
                Decision(margin, cfg["on_bottom_m"]),
                Decision(flowin, cfg["pumping_lpm"]),
                Decision(rpm, cfg["rotating_rpm"]),
                Decision(abs(v), cfg["moving_mps"]),
            ],
            back_reaming=v > 0,
        )

    if not flags.on_bottom and flags.pumping:
        return RuleResult(
            "circulating",
            "R7",
            [Decision(margin, cfg["on_bottom_m"]), Decision(flowin, cfg["pumping_lpm"])],
        )

    if not flags.on_bottom and not flags.pumping and flags.moving:
        v = flags.v
        assert v is not None
        deciding = [
            Decision(margin, cfg["on_bottom_m"]),
            Decision(flowin, cfg["pumping_lpm"]),
            Decision(abs(v), cfg["moving_mps"]),
        ]
        if v < 0:
            return RuleResult("trip_in", "R8", deciding)
        if v > 0:
            return RuleResult("trip_out", "R9", deciding)

    return RuleResult("unknown", "R10")
