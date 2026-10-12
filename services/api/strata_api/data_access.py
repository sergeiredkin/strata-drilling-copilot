"""Shared static-export reading helpers. Every route reads from `settings.data_dir` — the same
tree `make export`/`make fixtures` write — never recomputing anything (docs/03_ARCHITECTURE.md
§2). `well_id`/`evidence_id` are validated by the route's path-parameter type (the generated
`WellId`/`EvidenceId` regex) before these helpers ever see them, so path traversal via a crafted
id is not a concern here — but every lookup still resolves strictly under `data_dir`.
"""

from __future__ import annotations

import json
import struct
from typing import Any

from fastapi import HTTPException

from .settings import Settings

_STRS_MAGIC = b"STRS"
_STRS_HEADER = "<4sIdfI"


def read_json(settings: Settings, relative_path: str) -> Any:
    path = settings.data_dir / relative_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"not found: {relative_path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_or_default(settings: Settings, relative_path: str, default: Any) -> Any:
    path = settings.data_dir / relative_path
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_evidence(settings: Settings, evidence_id: str) -> dict[str, Any]:
    shard_of = read_json_or_default(settings, "evidence/shards.json", {})
    shard = shard_of.get(evidence_id)
    if shard is None:
        raise HTTPException(status_code=404, detail=f"unknown evidence id: {evidence_id}")
    shard_records = read_json(settings, f"evidence/{shard}.json")
    record: dict[str, Any] | None = shard_records.get(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"unknown evidence id: {evidence_id}")
    return record


def assemble_channel_level(settings: Settings, well_id: str, channel: str, level: int) -> bytes:
    """Concatenates every on-disk chunk of one channel's pyramid level
    (`export/series.py`'s `export_channel_series` output) into a single STRS block — the live
    `HttpSource.seriesChunk` always requests a whole level in one call (no chunk index), unlike
    static mode which fetches each chunk file directly. `decodeStrsBlock` on the client expects
    exactly one header, so the chunks must be merged here, not just concatenated as separate
    STRS blocks."""
    index = read_json(settings, f"wells/{well_id}/series/index.json")
    channel_meta = index.get("channels", {}).get(channel)
    if channel_meta is None:
        raise HTTPException(status_code=404, detail=f"well {well_id} has no channel {channel}")
    level_meta = next((lv for lv in channel_meta["levels"] if lv["level"] == level), None)
    if level_meta is None:
        raise HTTPException(status_code=404, detail=f"well {well_id} channel {channel} has no level {level}")

    chunks = sorted(level_meta["chunks"], key=lambda c: c["i"])
    if not chunks:
        header = struct.pack(_STRS_HEADER, _STRS_MAGIC, 0, 0.0, float(level_meta["bucket_s"]), 0)
        return header

    mins: list[bytes] = []
    maxs: list[bytes] = []
    total_n = 0
    t0_ms = float(chunks[0]["t0"])
    bucket_s = float(level_meta["bucket_s"])
    for chunk_meta in chunks:
        chunk_path = settings.data_dir / "wells" / well_id / chunk_meta["file"]
        if not chunk_path.is_file():
            raise HTTPException(status_code=404, detail=f"missing series chunk file: {chunk_meta['file']}")
        data = chunk_path.read_bytes()
        magic, n, _t0, _bucket_s, _reserved = struct.unpack_from(_STRS_HEADER, data, 0)
        if magic != _STRS_MAGIC:
            raise HTTPException(status_code=500, detail=f"corrupt STRS chunk: {chunk_meta['file']}")
        body = data[24:]
        mins.append(body[: n * 4])
        maxs.append(body[n * 4 : n * 8])
        total_n += n

    header = struct.pack(_STRS_HEADER, _STRS_MAGIC, total_n, t0_ms, bucket_s, 0)
    return header + b"".join(mins) + b"".join(maxs)


def data_dir_ready(settings: Settings) -> bool:
    return (settings.data_dir / "wells.json").is_file()


def ensure_data_dir_ready(settings: Settings) -> None:
    if not data_dir_ready(settings):
        raise HTTPException(
            status_code=503,
            detail=f"no export found at {settings.data_dir} — run 'make fixtures' or 'make export' first",
        )


def well_dir_exists(settings: Settings, well_id: str) -> bool:
    return (settings.data_dir / "wells" / well_id).is_dir()


def require_well(settings: Settings, well_id: str) -> None:
    if not well_dir_exists(settings, well_id):
        raise HTTPException(status_code=404, detail=f"unknown well id: {well_id}")
