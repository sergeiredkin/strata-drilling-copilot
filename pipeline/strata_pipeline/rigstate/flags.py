"""Rig-state boolean flags — docs/07_DATA_AND_ALGORITHMS.md §4. Each flag is `None` whenever one
of its inputs is `None` (a gap), so the caller can tell "false" apart from "unknown"."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Flags:
    on_bottom: bool | None
    in_slips: bool | None
    rotating: bool | None
    pumping: bool | None
    moving: bool | None
    near_bottom: bool | None
    holedepth_minus_bitdepth: float | None
    v: float | None


def compute_flags(
    hkld: float | None,
    bitdepth: float | None,
    holedepth: float | None,
    rpm: float | None,
    flowin: float | None,
    v: float | None,
    hl_slips: float,
    cfg: dict[str, Any],
) -> Flags:
    depth_margin = None if bitdepth is None or holedepth is None else holedepth - bitdepth
    return Flags(
        on_bottom=None if depth_margin is None else depth_margin <= cfg["on_bottom_m"],
        in_slips=None if hkld is None else hkld < hl_slips,
        rotating=None if rpm is None else rpm > cfg["rotating_rpm"],
        pumping=None if flowin is None else flowin > cfg["pumping_lpm"],
        moving=None if v is None else abs(v) > cfg["moving_mps"],
        near_bottom=None if depth_margin is None else depth_margin < cfg["near_bottom_m"],
        holedepth_minus_bitdepth=depth_margin,
        v=v,
    )
