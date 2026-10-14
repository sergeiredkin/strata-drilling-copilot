"""T13.2 live replay — the server-side half of `WS /replay/{well_id}`
(docs/03_ARCHITECTURE.md §4: "server streams L0 samples + state transitions + alert events at
speed"). `merge_replay_events` is the same merge StaticSource's `mergeReplayEvents` does
client-side (apps/web/src/data/replayPlayer.ts) — one L0 chunk's worth of every replay channel
decoded at a time, never the whole well's samples held in memory — kept as a plain generator so
it's testable without a WebSocket. The route (`routes/replay.py`) only adds the timer and the
socket.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Iterator
from typing import Any

from .data_access import read_json_or_default
from .settings import Settings

_STRS_HEADER_FMT = "<4sIdfI"
_STRS_MAGIC = b"STRS"
_STRS_HEADER_SIZE = 24

REPLAY_CHANNELS: list[str] = [
    "HKLD", "BPOS", "WOB", "RPM", "TORQ", "SPP", "FLOWIN", "BITDEPTH", "HOLEDEPTH",
]


def _decode_chunk_mins(data: bytes) -> tuple[float, float, list[float]]:
    magic, n, t0_ms, bucket_s, _reserved = struct.unpack_from(_STRS_HEADER_FMT, data, 0)
    if magic != _STRS_MAGIC:
        raise ValueError("corrupt STRS chunk: bad magic")
    mins = list(struct.unpack_from(f"<{n}f", data, _STRS_HEADER_SIZE))
    return float(t0_ms), float(bucket_s), mins


def _level0_chunks(index: dict[str, Any], channel: str) -> list[dict[str, Any]]:
    channel_meta = index.get("channels", {}).get(channel)
    if channel_meta is None:
        return []
    level0 = next((lv for lv in channel_meta["levels"] if lv["level"] == 0), None)
    return level0["chunks"] if level0 else []


def merge_replay_events(settings: Settings, well_id: str, from_t: float) -> Iterator[dict[str, Any]]:
    """Yields `ReplayEvent`-shaped dicts (`sample`/`state`/`alert`) in time order, `t >= from_t`.
    Empty for a well with no series export at all — an honest empty stream, not an error."""
    index = read_json_or_default(settings, f"wells/{well_id}/series/index.json", {"channels": {}})
    channels = [ch for ch in REPLAY_CHANNELS if ch in index.get("channels", {})]

    state_alerts = [
        e for e in read_json_or_default(settings, f"wells/{well_id}/replay_events.json", []) if e["t"] >= from_t
    ]
    state_alerts.sort(key=lambda e: e["t"])
    sa_idx = 0

    driver = channels[0] if channels else None
    chunk_metas = (
        sorted((c for c in _level0_chunks(index, driver) if c["t1"] > from_t), key=lambda c: c["t0"])
        if driver
        else []
    )

    for chunk_meta in chunk_metas:
        decoded: dict[str, tuple[float, float, list[float]]] = {}
        for ch in channels:
            ch_chunk = next((c for c in _level0_chunks(index, ch) if c["t0"] == chunk_meta["t0"]), None)
            if ch_chunk is None:
                continue
            path = settings.data_dir / "wells" / well_id / ch_chunk["file"]
            if not path.is_file():
                continue
            decoded[ch] = _decode_chunk_mins(path.read_bytes())
        if not decoded:
            continue

        t0_ms, bucket_s, first_mins = next(iter(decoded.values()))
        for i in range(len(first_mins)):
            t = t0_ms + i * bucket_s * 1000.0
            if t < from_t:
                continue
            while sa_idx < len(state_alerts) and state_alerts[sa_idx]["t"] <= t:
                yield state_alerts[sa_idx]
                sa_idx += 1
            values: dict[str, float | None] = {}
            for ch, (_ct0, _cbucket, mins) in decoded.items():
                v = mins[i] if i < len(mins) else None
                values[ch] = None if v is None or math.isnan(v) else v
            yield {"type": "sample", "t": t, "values": values}

    while sa_idx < len(state_alerts):
        yield state_alerts[sa_idx]
        sa_idx += 1


__all__ = ["REPLAY_CHANNELS", "merge_replay_events"]
