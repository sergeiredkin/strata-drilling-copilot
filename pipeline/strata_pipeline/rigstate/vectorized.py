"""Vectorized rig-state classification — numerically identical to `rules.classify_sample` run
per-sample (that scalar version stays as the tested reference implementation; this is what
`classify.run_rigstate` actually calls). Found necessary against real data: the original
per-sample Python loop allocated a dict + `Flags` dataclass + `RuleResult` (+ 2-4 nested
`Decision` objects) for every single sample — for a ~1M-sample well that's several million small
heap objects, which turned out to be the dominant remaining memory/time cost even after
qc/spikes.py, qc/frozen.py, and rigstate/preprocess.py were vectorized (see those modules'
docstrings). This computes the same R0-R10 cascade (docs/07_DATA_AND_ALGORITHMS.md §4) and the
same "decisive" confidence test as plain numpy boolean-mask operations over the whole well at
once, with no per-sample Python object at all."""

from __future__ import annotations

from typing import Any

import numpy as np

from .rules import CORE_CHANNELS

_EPS = 1e-9


def trip_directions_vectorized(bitdepth: np.ndarray, window_samples: int) -> np.ndarray:
    """Sign of the net BITDEPTH change over the trailing `window_samples` — "trip_in" (net > 0),
    "trip_out" (net < 0), or None (no net change, or either endpoint missing)."""
    n = len(bitdepth)
    lo_idx = np.maximum(0, np.arange(n) - window_samples)
    net = bitdepth - bitdepth[lo_idx]
    out = np.full(n, None, dtype=object)
    with np.errstate(invalid="ignore"):
        out[net > 0] = "trip_in"
        out[net < 0] = "trip_out"
    return out


def _relative_margin(value: np.ndarray, threshold: float) -> np.ndarray:
    return np.abs(value - threshold) / max(abs(threshold), _EPS)


def classify_samples_vectorized(
    core: dict[str, np.ndarray],
    v: np.ndarray,
    trip_direction: np.ndarray,
    hl_slips: float,
    cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """`core` has every key in CORE_CHANNELS, each a float64 numpy array with NaN at gaps, same
    length as `v`/`trip_direction`. Returns (state, rule_id, decisive, back_reaming) — all numpy
    arrays, `state`/`rule_id` as object arrays of str, `decisive`/`back_reaming` as bool."""
    n = len(v)
    hkld, bpos, flowin, rpm, bitdepth, holedepth = (core[c] for c in CORE_CHANNELS)

    valid_core = ~(
        np.isnan(hkld) | np.isnan(bpos) | np.isnan(flowin) | np.isnan(rpm) | np.isnan(bitdepth) | np.isnan(holedepth)
    )
    margin = holedepth - bitdepth  # NaN-safe: NaN propagates, comparisons below are False for NaN

    on_bottom = margin <= cfg["on_bottom_m"]
    near_bottom = margin < cfg["near_bottom_m"]
    in_slips = hkld < hl_slips
    rotating = rpm > cfg["rotating_rpm"]
    pumping = flowin > cfg["pumping_lpm"]
    with np.errstate(invalid="ignore"):
        moving = np.abs(v) > cfg["moving_mps"]

    state = np.full(n, "unknown", dtype=object)
    rule_id = np.full(n, "R0", dtype=object)
    back_reaming = np.zeros(n, dtype=bool)
    decisive = np.zeros(n, dtype=bool)
    decided = ~valid_core  # R0 (core gap) samples are already settled

    margin_on_bottom = _relative_margin(margin, cfg["on_bottom_m"])
    margin_pumping = _relative_margin(flowin, cfg["pumping_lpm"])
    margin_rotating = _relative_margin(rpm, cfg["rotating_rpm"])
    with np.errstate(invalid="ignore"):
        margin_moving = _relative_margin(np.abs(v), cfg["moving_mps"])
    margin_slips = _relative_margin(hkld, hl_slips)
    margin_near_bottom = _relative_margin(margin, cfg["near_bottom_m"])
    margin_out_of_hole = _relative_margin(bitdepth, cfg["out_of_hole_bitdepth_m"])
    mf = cfg["confidence_margin_frac"]

    def apply(fire: np.ndarray, new_state: np.ndarray | str, new_rule: str, decisive_mask: np.ndarray) -> None:
        nonlocal decided
        fire = fire & ~decided
        state[fire] = new_state if isinstance(new_state, str) else new_state[fire]
        rule_id[fire] = new_rule
        decisive[fire] = decisive_mask[fire]
        decided = decided | fire

    # R1: out_of_hole
    r1 = (bitdepth < cfg["out_of_hole_bitdepth_m"]) & ~pumping
    apply(r1, "out_of_hole", "R1", (margin_out_of_hole > mf) & (margin_pumping > mf))

    # R2/R3: connection / trip (direction from the net-BITDEPTH trend; defaults to trip_out)
    r2 = in_slips & near_bottom
    apply(r2, "connection", "R2", (margin_slips > mf) & (margin_near_bottom > mf))

    r3 = in_slips & ~near_bottom
    trip_state_r3 = np.where((trip_direction == "trip_in") | (trip_direction == "trip_out"), trip_direction, "trip_out")
    apply(r3, trip_state_r3, "R3", (margin_slips > mf) & (margin_near_bottom > mf))

    # R4/R5: rotary_drilling / sliding
    r4 = on_bottom & pumping & rotating
    apply(r4, "rotary_drilling", "R4", (margin_on_bottom > mf) & (margin_pumping > mf) & (margin_rotating > mf))

    r5 = on_bottom & pumping & ~rotating
    apply(r5, "sliding", "R5", (margin_on_bottom > mf) & (margin_pumping > mf) & (margin_rotating > mf))

    # R6: reaming (back_reaming when v > 0)
    r6 = ~on_bottom & pumping & rotating & moving
    r6_decisive = (margin_on_bottom > mf) & (margin_pumping > mf) & (margin_rotating > mf) & (margin_moving > mf)
    fire6 = r6 & ~decided
    back_reaming[fire6] = v[fire6] > 0
    apply(r6, "reaming", "R6", r6_decisive)

    # R7: circulating
    r7 = ~on_bottom & pumping
    apply(r7, "circulating", "R7", (margin_on_bottom > mf) & (margin_pumping > mf))

    # R8/R9: trip_in / trip_out from velocity sign
    r89_base = ~on_bottom & ~pumping & moving
    r89_decisive = (margin_on_bottom > mf) & (margin_pumping > mf) & (margin_moving > mf)
    with np.errstate(invalid="ignore"):
        r8 = r89_base & (v < 0)
        r9 = r89_base & (v > 0)
    apply(r8, "trip_in", "R8", r89_decisive)
    apply(r9, "trip_out", "R9", r89_decisive)

    # R10: everything else still undecided
    r10 = ~decided
    state[r10] = "unknown"
    rule_id[r10] = "R10"
    decisive[r10] = False

    return state, rule_id, decisive, back_reaming
