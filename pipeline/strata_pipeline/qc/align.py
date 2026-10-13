"""Aligns QC's per-channel output (each on its own 1 s grid, starting at that channel's own
first surviving sample) onto one shared 1 s time axis spanning the whole well — rigstate and the
exporter both need every core channel addressable by the same index. Never fills a channel's
missing span with anything but `NaN`; a channel that starts later than the well's overall first
sample is simply `NaN` before that point, same as any other gap."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .pipeline import ChannelQCResult


def align_well_channels(
    channels: dict[str, ChannelQCResult], grid_seconds: float = 1.0
) -> tuple[list[datetime], dict[str, np.ndarray]]:
    starts = [c.clean_t0 for c in channels.values() if c.clean_t0 is not None]
    if not starts:
        return [], {name: np.array([], dtype=np.float32) for name in channels}

    step = timedelta(seconds=grid_seconds)
    # Each channel's own grid is already arithmetic (clean_t0 + i * step — see
    # qc.resample.resample_to_grid), so its span's end point is derived the same way instead of
    # keeping a full per-channel datetime list just to read its last element.
    ends = [c.clean_t0 + step * (len(c.clean_values) - 1) for c in channels.values() if c.clean_t0 is not None]
    t0 = min(starts)
    t1 = max(ends)
    n = int(round((t1 - t0).total_seconds() / grid_seconds)) + 1
    t = [t0 + step * i for i in range(n)]

    aligned: dict[str, np.ndarray] = {}
    for name, result in channels.items():
        out = np.full(n, np.nan, dtype=np.float32)
        if result.clean_t0 is not None and len(result.clean_values):
            # By construction t0 == min(starts) and t1 == max(ends), so this channel's own span
            # always falls entirely inside [0, n) — no per-element bounds check needed.
            offset = int(round((result.clean_t0 - t0).total_seconds() / grid_seconds))
            out[offset : offset + len(result.clean_values)] = result.clean_values
        aligned[name] = out
    return t, aligned
