"""STRS binary min/max pyramid writer.

Format: `04_DATA_CONTRACTS.md` §4. Levels: `03_ARCHITECTURE.md` §3.4.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

MAGIC = b"STRS"
LEVEL_BUCKET_S: list[float] = [1, 8, 64, 512, 4096, 32768, 262144]
# L0 chunk 6 h, L1 chunk 48 h, L2+ one chunk for the whole well (None = unbounded).
LEVEL_CHUNK_S: dict[int, float | None] = {0: 6 * 3600, 1: 48 * 3600}


def write_strs(
    path: Path, t0_ms: float, bucket_s: float, mins: np.ndarray, maxs: np.ndarray
) -> None:
    """Writes one STRS chunk: 24-byte header + f32[n] min + f32[n] max, little-endian."""
    n = len(mins)
    header = struct.pack("<4sIdfI", MAGIC, n, float(t0_ms), float(bucket_s), 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(header)
        f.write(np.asarray(mins, dtype="<f4").tobytes())
        f.write(np.asarray(maxs, dtype="<f4").tobytes())


def read_strs(path: Path) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Reads one STRS chunk back. Used only by tests (the app reads via the TS decoder)."""
    data = path.read_bytes()
    magic, n, t0_ms, bucket_s, _reserved = struct.unpack_from("<4sIdfI", data, 0)
    if magic != MAGIC:
        raise ValueError(f"bad STRS magic in {path}: {magic!r}")
    body = data[24:]
    mins = np.frombuffer(body, dtype="<f4", count=n)
    maxs = np.frombuffer(body, dtype="<f4", count=n, offset=n * 4)
    return t0_ms, bucket_s, mins.copy(), maxs.copy()


def _downsample(
    mins: np.ndarray, maxs: np.ndarray, factor: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    n = len(mins)
    pad = (-n) % factor
    if pad:
        mins = np.concatenate([mins, np.full(pad, np.nan, dtype="f4")])
        maxs = np.concatenate([maxs, np.full(pad, np.nan, dtype="f4")])
    mins2 = mins.reshape(-1, factor)
    maxs2 = maxs.reshape(-1, factor)
    all_nan_rows = np.all(np.isnan(mins2), axis=1)
    with np.errstate(invalid="ignore", all="ignore"):
        out_min = np.nanmin(mins2, axis=1)
        out_max = np.nanmax(maxs2, axis=1)
    out_min[all_nan_rows] = np.nan
    out_max[all_nan_rows] = np.nan
    return out_min.astype("f4"), out_max.astype("f4")


def nan_run_gaps(
    t0_ms: float, bucket_s: float, values: np.ndarray, reason: str = "no_data"
) -> list[dict[str, float | str]]:
    """Scans an L0 (1-sample-per-bucket) array for NaN runs and returns GapInterval dicts."""
    isn = np.isnan(values)
    gaps: list[dict[str, float | str]] = []
    n = len(values)
    i = 0
    while i < n:
        if isn[i]:
            j = i
            while j < n and isn[j]:
                j += 1
            gaps.append(
                {
                    "t0": t0_ms + i * bucket_s * 1000,
                    "t1": t0_ms + j * bucket_s * 1000,
                    "reason": reason,
                }
            )
            i = j
        else:
            i += 1
    return gaps


def export_channel_series(
    well_dir: Path,
    channel: str,
    unit: str,
    source: str,
    t0_ms: float,
    values: np.ndarray,
    gap_reason: str = "no_data",
) -> dict[str, object]:
    """`values` is a uniform 1 Hz (bucket_s=1) series, NaN = gap. Writes every pyramid level's
    chunks under `well_dir/series/{channel}/L{n}/{i}.bin` and returns the SeriesIndex channel
    entry (unit, source, levels, gaps)."""
    gaps = nan_run_gaps(t0_ms, 1.0, values, gap_reason)

    mins = np.asarray(values, dtype="f4")
    maxs = np.asarray(values, dtype="f4")
    levels_meta = []
    for level, bucket_s in enumerate(LEVEL_BUCKET_S):
        if level > 0:
            mins, maxs = _downsample(mins, maxs, factor=8)
        chunk_s = LEVEL_CHUNK_S.get(level)
        n_total = len(mins)
        chunk_len = n_total if chunk_s is None else max(1, int(chunk_s / bucket_s))
        chunks_meta = []
        ci = 0
        for start in range(0, max(n_total, 1), chunk_len):
            end = min(start + chunk_len, n_total)
            if end <= start:
                continue
            chunk_t0 = t0_ms + start * bucket_s * 1000
            chunk_t1 = t0_ms + end * bucket_s * 1000
            fname = f"series/{channel}/L{level}/{ci}.bin"
            write_strs(well_dir / fname, chunk_t0, bucket_s, mins[start:end], maxs[start:end])
            chunks_meta.append(
                {"i": ci, "t0": chunk_t0, "t1": chunk_t1, "n": end - start, "file": fname}
            )
            ci += 1
        levels_meta.append({"level": level, "bucket_s": bucket_s, "chunks": chunks_meta})

    return {"unit": unit, "source": source, "levels": levels_meta, "gaps": gaps}
