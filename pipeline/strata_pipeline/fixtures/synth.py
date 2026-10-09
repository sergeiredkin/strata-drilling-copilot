"""Deterministic synthetic rig-state + sensor generator for fixtures.

The approach mirrors `docs/design/comps/S2-Workspace.dc.html`'s generator: a rig-state script
(a list of (state, t0, t1) segments) drives per-channel profile functions, rather than the other
way around — the ground-truth state is the input, sensors are derived from it, same as a real
rig would produce sensor readings consistent with what it was doing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .wells import WellSpec

HZ = 1.0  # native sample rate inside the dense window (04_DATA_CONTRACTS.md §4; see ADR 0006)
DAY_S = 86_400

# Rig-state thresholds, 07_DATA_AND_ALGORITHMS.md §4 (for reference / internal consistency only —
# fixtures assign state directly, they do not run the classifier).
HL_SLIPS_FRACTION = 0.3  # in_slips if HKLD below this fraction of on-bottom HKLD

# (t0_ms, t1_ms, code, narrative, report_date, npt, md_from, md_to)
DdrRowTuple = tuple[float, float, str, str, str, bool, float | None, float | None]


@dataclass
class ChannelSeries:
    unit: str
    values: np.ndarray  # 1 Hz, NaN = gap


@dataclass
class WellDetail:
    spec: WellSpec
    t0_ms: float
    channels: dict[str, ChannelSeries] = field(default_factory=dict)
    # ground-truth rig-state intervals: (t0_ms, t1_ms, state, p)
    state_intervals: list[tuple[float, float, str, float]] = field(default_factory=list)
    ddr_rows: list[DdrRowTuple] = field(default_factory=list)
    md_start: float = 0.0
    md_end: float = 0.0


def _smooth_noise(
    rng: np.random.Generator, n: int, scale: float, period_s: float = 37.0
) -> np.ndarray:
    """Band-limited-ish noise: a slow sine plus small iid jitter, so traces look like real
    sensor chatter rather than literal white noise."""
    t = np.arange(n)
    phase = rng.uniform(0, 2 * np.pi)
    slow = np.sin(2 * np.pi * t / period_s + phase)
    jitter = rng.normal(0, 0.3, n)
    return scale * (0.7 * slow + 0.3 * jitter)


# Per-state baseline fraction of each channel's "full scale" (same shape of idea as the comp's
# `prof` table), used for every channel except BITDEPTH/HOLEDEPTH which are integrated instead.
_STATE_PROFILE: dict[str, dict[str, float]] = {
    "rotary_drilling": {
        "hkld": 0.50, "wob": 0.60, "rpm": 0.70, "torq": 0.55, "spp": 0.72, "flow": 0.75,
    },
    "sliding": {
        "hkld": 0.48, "wob": 0.55, "rpm": 0.05, "torq": 0.45, "spp": 0.74, "flow": 0.75,
    },
    "connection": {
        "hkld": 0.18, "wob": 0.04, "rpm": 0.02, "torq": 0.05, "spp": 0.03, "flow": 0.02,
    },
    "reaming": {
        "hkld": 0.62, "wob": 0.10, "rpm": 0.70, "torq": 0.35, "spp": 0.60, "flow": 0.70,
    },
    "circulating": {
        "hkld": 0.60, "wob": 0.04, "rpm": 0.25, "torq": 0.10, "spp": 0.68, "flow": 0.72,
    },
    "trip_in": {
        "hkld": 0.55, "wob": 0.02, "rpm": 0.01, "torq": 0.03, "spp": 0.01, "flow": 0.01,
    },
    "trip_out": {
        "hkld": 0.70, "wob": 0.02, "rpm": 0.01, "torq": 0.03, "spp": 0.01, "flow": 0.01,
    },
    "out_of_hole": {"hkld": 0.10, "wob": 0.0, "rpm": 0.0, "torq": 0.0, "spp": 0.0, "flow": 0.0},
    "unknown": {"hkld": 0.40, "wob": 0.02, "rpm": 0.02, "torq": 0.05, "spp": 0.30, "flow": 0.30},
}

# (full-scale value, unit) per channel — chosen so rotary_drilling lands near typical Volve-scale
# readings (hookload ~900 kN, SPP ~210 bar, flow ~2400 L/min, etc).
_FULL_SCALE: dict[str, tuple[float, str]] = {
    "hkld": (1800.0, "kN"),
    "wob": (300.0, "kN"),
    "rpm": (170.0, "rpm"),
    "torq": (25.0, "kN.m"),
    "spp": (300.0, "bar"),
    "flow": (3200.0, "L/min"),
}

_CHANNEL_KEY_TO_ID = {
    "hkld": "HKLD",
    "wob": "WOB",
    "rpm": "RPM",
    "torq": "TORQ",
    "spp": "SPP",
    "flow": "FLOWIN",
}


def build_segments(
    rng: np.random.Generator,
    total_s: int,
    slow_connection_prob: float,
    reaming_in_drill_prob: float,
    include_trip: bool,
) -> list[tuple[int, int, str]]:
    """Builds a repeating drill/connection "stand cycle" over [0, total_s), seconds, with
    occasional slow connections and short reaming blocks embedded inside drilling (both of
    which later get DDR-coded as DRILL, producing the deliberate sensor/report mismatches)."""
    segs: list[tuple[int, int, str]] = []
    t = 0

    if include_trip:
        trip_in_s = int(rng.uniform(20 * 60, 30 * 60))
        trip_out_s = int(rng.uniform(15 * 60, 22 * 60))
        segs.append((t, t + trip_in_s, "trip_in"))
        t += trip_in_s
        segs.append((t, t + trip_out_s, "trip_out"))
        t += trip_out_s

    while t < total_s:
        drill_s = int(rng.uniform(18 * 60, 26 * 60))
        drill_end = min(t + drill_s, total_s)

        if rng.random() < reaming_in_drill_prob and drill_end - t > 6 * 60:
            ream_start = t + int(rng.uniform(3 * 60, drill_end - t - 3 * 60))
            ream_len = int(rng.uniform(90, 180))
            segs.append((t, ream_start, "rotary_drilling"))
            segs.append((ream_start, ream_start + ream_len, "reaming"))
            segs.append((ream_start + ream_len, drill_end, "rotary_drilling"))
        else:
            segs.append((t, drill_end, "rotary_drilling"))
        t = drill_end
        if t >= total_s:
            break

        if rng.random() < 0.12:
            circ_s = int(rng.uniform(3 * 60, 6 * 60))
            circ_end = min(t + circ_s, total_s)
            segs.append((t, circ_end, "circulating"))
            t = circ_end
            if t >= total_s:
                break

        slow = rng.random() < slow_connection_prob
        conn_s = int(rng.uniform(9 * 60, 15 * 60) if slow else rng.uniform(3 * 60, 7 * 60))
        conn_end = min(t + conn_s, total_s)
        segs.append((t, conn_end, "connection"))
        t = conn_end

    return segs


def _profile_value(channel: str, state: str, rng: np.random.Generator, n: int) -> np.ndarray:
    full_scale, _unit = _FULL_SCALE[channel]
    frac = _STATE_PROFILE.get(state, _STATE_PROFILE["unknown"])[channel]
    base = frac * full_scale
    noise_scale = 0.03 * full_scale if frac > 0.05 else 0.01 * full_scale
    return np.clip(base + _smooth_noise(rng, n, noise_scale), 0, None)


def synthesize_well(
    spec: WellSpec, seed: int, md_start: float = 2200.0, rop_m_per_h: float = 22.0
) -> WellDetail:
    """Builds `spec.dense_days` days of 1 Hz sensor + ground-truth rig-state data, one 4-minute
    `no_data` gap per day, and DDR rows at 15-30 min granularity with deliberate mismatches
    (reaming-in-drill, slow connections) and a realistic normalized-code vocabulary."""
    rng = np.random.default_rng(seed)
    total_s = spec.dense_days * DAY_S
    t0_ms = 1_700_000_000_000.0  # fixed epoch anchor so fixtures are reproducible across runs

    is_sparse = spec.id == "15_9-F-5"
    segs = build_segments(
        rng,
        total_s,
        slow_connection_prob=0.35 if spec.id == "15_9-F-11_A" else 0.1,
        reaming_in_drill_prob=0.25 if spec.id == "15_9-F-11_A" else 0.08,
        include_trip=spec.id == "15_9-F-11_A",
    )

    n = total_s
    channel_arrays: dict[str, np.ndarray] = {k: np.empty(n, dtype="f4") for k in _FULL_SCALE}
    holedepth = np.empty(n, dtype="f4")
    bitdepth = np.empty(n, dtype="f4")

    md = md_start
    rop_m_per_s = rop_m_per_h / 3600.0
    state_intervals: list[tuple[float, float, str, float]] = []

    for seg_t0, seg_t1, state in segs:
        length = seg_t1 - seg_t0
        if length <= 0:
            continue
        for ch in _FULL_SCALE:
            channel_arrays[ch][seg_t0:seg_t1] = _profile_value(ch, state, rng, length)

        on_bottom = state in ("rotary_drilling", "sliding")
        if on_bottom:
            md_path = md + np.arange(length) * rop_m_per_s
            holedepth[seg_t0:seg_t1] = md_path
            bitdepth[seg_t0:seg_t1] = md_path
            md = float(md_path[-1]) + rop_m_per_s
        else:
            holedepth[seg_t0:seg_t1] = md
            off_bottom_offset = {
                "reaming": rng.uniform(5, 25),
                "circulating": rng.uniform(0, 3),
                "trip_in": rng.uniform(0, md_start * 0.3),
                "trip_out": rng.uniform(0, md_start * 0.3),
            }.get(state, 0.0)
            bitdepth[seg_t0:seg_t1] = max(md - off_bottom_offset, 0.0)

        p = float(rng.uniform(0.75, 0.98))
        state_intervals.append((t0_ms + seg_t0 * 1000, t0_ms + seg_t1 * 1000, state, p))

    channels: dict[str, ChannelSeries] = {}
    for ch, arr in channel_arrays.items():
        channels[_CHANNEL_KEY_TO_ID[ch]] = ChannelSeries(unit=_FULL_SCALE[ch][1], values=arr)
    channels["HOLEDEPTH"] = ChannelSeries(unit="m", values=holedepth)
    channels["BITDEPTH"] = ChannelSeries(unit="m", values=bitdepth)

    # One 4-minute no_data gap per day (every well); F-5 additionally loses an entire day of
    # time-log channels (not depth/DDR) to its sparse/partial time_logs coverage.
    for day in range(spec.dense_days):
        gap_start = day * DAY_S + int(rng.uniform(2 * 3600, 20 * 3600))
        gap_end = min(gap_start + 4 * 60, total_s)
        for series in channels.values():
            series.values[gap_start:gap_end] = np.nan
        state_intervals.append((t0_ms + gap_start * 1000, t0_ms + gap_end * 1000, "unknown", 0.0))

    if is_sparse and spec.dense_days >= 2:
        missing_day = 1
        lo, hi = missing_day * DAY_S, (missing_day + 1) * DAY_S
        for key in ("HKLD", "WOB", "RPM", "TORQ", "SPP", "FLOWIN"):
            channels[key].values[lo:hi] = np.nan

    state_intervals.sort(key=lambda s: s[0])
    ddr_rows = _build_ddr_rows(spec, segs, t0_ms, holedepth)

    detail = WellDetail(
        spec=spec,
        t0_ms=t0_ms,
        channels=channels,
        state_intervals=state_intervals,
        ddr_rows=ddr_rows,
        md_start=md_start,
        md_end=md,
    )
    return detail


_DDR_NARRATIVES = {
    "DRILL": "Drilling {section} hole from {md_from:.0f} m to {md_to:.0f} m.",
    "DRILL_SLOW": (
        "Drilling {section} hole from {md_from:.0f} m to {md_to:.0f} m. "
        "Slow connections due to tight hole."
    ),
    "CIRC": "Circulating bottoms up prior to continuing operations.",
    "TRIP": "Tripping pipe to change bit.",
}


def _build_ddr_rows(
    spec: WellSpec, segs: list[tuple[int, int, str]], t0_ms: float, holedepth: np.ndarray
) -> list[DdrRowTuple]:
    """Aggregates the fine-grained rig-state segments into 15-30 min DDR rows. Reaming blocks
    embedded inside drilling and the connections around them are folded into a DRILL row (DDR
    never reports reaming unless it dominates a window) — this is the deliberate source of the
    'unreported reaming' ILT category and of sensor/report mismatches."""
    rows: list[DdrRowTuple] = []
    bucket_s = 20 * 60
    total_s = segs[-1][1] if segs else 0
    section_label = spec.sections[-1] if spec.sections else ""

    bucket_start = 0
    while bucket_start < total_s:
        bucket_end = min(bucket_start + bucket_s, total_s)
        # dominant ground-truth state within this bucket
        durations: dict[str, int] = {}
        for seg_t0, seg_t1, state in segs:
            overlap = min(seg_t1, bucket_end) - max(seg_t0, bucket_start)
            if overlap > 0:
                durations[state] = durations.get(state, 0) + overlap
        dominant = max(durations, key=lambda s: durations[s]) if durations else "unknown"

        code_map = {
            "rotary_drilling": "DRILL",
            "sliding": "DRILL",
            "connection": "DRILL",
            "reaming": "DRILL",  # reaming inside a drilling window is reported as DRILL
            "circulating": "CIRC",
            "trip_in": "TRIP",
            "trip_out": "TRIP",
            "out_of_hole": "OTHER",
            "unknown": "OTHER",
        }
        code = code_map.get(dominant, "OTHER")
        had_reaming = durations.get("reaming", 0) > 0
        had_slow_conn = durations.get("connection", 0) > 8 * 60

        day_idx = bucket_start // DAY_S
        report_date = f"2015-06-{(1 + day_idx):02d}"
        md_from: float | None = None
        md_to: float | None = None
        if code == "DRILL":
            template = "DRILL_SLOW" if had_slow_conn else "DRILL"
            md_from = float(holedepth[bucket_start])
            md_to = float(holedepth[bucket_end - 1])
            narrative = _DDR_NARRATIVES[template].format(
                section=section_label, md_from=md_from, md_to=md_to
            )
        else:
            narrative = _DDR_NARRATIVES.get(code, "Operations ongoing.")

        rows.append(
            (
                t0_ms + bucket_start * 1000,
                t0_ms + bucket_end * 1000,
                code,
                narrative + (" [unreported reaming observed]" if had_reaming else ""),
                report_date,
                False,
                md_from,
                md_to,
            )
        )
        bucket_start = bucket_end

    return rows
