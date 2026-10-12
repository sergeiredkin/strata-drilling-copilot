"""Aligns QC's per-channel output (each on its own 1 s grid, starting at that channel's own
first surviving sample) onto one shared 1 s time axis spanning the whole well — rigstate and the
exporter both need every core channel addressable by the same index. Never fills a channel's
missing span with anything but `None`; a channel that starts later than the well's overall first
sample is simply `None` before that point, same as any other gap."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import ChannelQCResult


def align_well_channels(
    channels: dict[str, ChannelQCResult], grid_seconds: float = 1.0
) -> tuple[list[datetime], dict[str, list[float | None]]]:
    non_empty = [c for c in channels.values() if c.clean_t]
    if not non_empty:
        return [], {name: [] for name in channels}

    t0 = min(c.clean_t[0] for c in non_empty)
    t1 = max(c.clean_t[-1] for c in non_empty)
    step = timedelta(seconds=grid_seconds)
    n = int(round((t1 - t0).total_seconds() / grid_seconds)) + 1
    t = [t0 + step * i for i in range(n)]

    aligned: dict[str, list[float | None]] = {}
    for name, result in channels.items():
        out: list[float | None] = [None] * n
        for ti, vi in zip(result.clean_t, result.clean_values, strict=True):
            idx = int(round((ti - t0).total_seconds() / grid_seconds))
            if 0 <= idx < n:
                out[idx] = vi
        aligned[name] = out
    return t, aligned
