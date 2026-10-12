"""Directional survey ingest -> `survey.parquet` — docs/07_DATA_AND_ALGORITHMS.md §2 ("MD, inc,
azi -> TVD/N/E by minimum curvature").

docs/DATA_INVENTORY.md: Volve's per-well survey export (`WellWellbore/<well>/<bore>/<name>_
ACTUAL`, no file extension) is a fixed-width text table that already carries TVD/N/E computed by
Statoil's own software (minimum curvature, per its own header). We compute TVD/N/E ourselves
from the raw MD/Inc/Azi columns (so the pipeline's own numbers are reproducible from first
principles, not copied) and keep the file's reference columns alongside ours purely for a QC
sanity check — CLAUDE.md's "never fabricate data" cuts both ways: don't silently trust a
pre-computed column either without checking it.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import polars as pl


def minimum_curvature(
    md: list[float], inc_deg: list[float], azi_deg: list[float]
) -> tuple[list[float], list[float], list[float]]:
    """Standard minimum-curvature method. Returns (tvd, north, east), all starting at 0 for the
    first station (matching the archive's own convention — see `parse_survey_file`'s docstring
    for why the first row isn't literally MD=0)."""
    n = len(md)
    tvd = [0.0] * n
    north = [0.0] * n
    east = [0.0] * n
    for i in range(1, n):
        md1, inc1, azi1 = md[i - 1], math.radians(inc_deg[i - 1]), math.radians(azi_deg[i - 1])
        md2, inc2, azi2 = md[i], math.radians(inc_deg[i]), math.radians(azi_deg[i])
        delta_md = md2 - md1
        cos_dl = math.cos(inc2 - inc1) - math.sin(inc1) * math.sin(inc2) * (1 - math.cos(azi2 - azi1))
        cos_dl = max(-1.0, min(1.0, cos_dl))
        dog_leg = math.acos(cos_dl)
        rf = 1.0 if dog_leg < 1e-9 else (2.0 / dog_leg) * math.tan(dog_leg / 2.0)

        d_tvd = (delta_md / 2.0) * (math.cos(inc1) + math.cos(inc2)) * rf
        d_north = (delta_md / 2.0) * (math.sin(inc1) * math.cos(azi1) + math.sin(inc2) * math.cos(azi2)) * rf
        d_east = (delta_md / 2.0) * (math.sin(inc1) * math.sin(azi1) + math.sin(inc2) * math.sin(azi2)) * rf

        tvd[i] = tvd[i - 1] + d_tvd
        north[i] = north[i - 1] + d_north
        east[i] = east[i - 1] + d_east
    return tvd, north, east


_ROW_RE = re.compile(
    r"^\s*(?P<md>[\d.]+)\s+(?P<inc>[\d.]+)\s+(?P<azi>[\d.]+)\s+(?P<tvd>[\d.]+)\s+"
    r"(?P<x>-?[\d.]+)\s+(?P<y>-?[\d.]+)"
)


def parse_survey_file(path: Path) -> pl.DataFrame:
    """Parses Volve's `SURVEY LIST` text block. The first row is the datum (KB or similar — not
    MD=0 at the rig floor), with inc/azi both 0 by convention; `minimum_curvature` is computed
    relative to that first row, matching how the file's own reference TVD column is anchored
    (both start the same value at row 0), so our computed TVD is directly comparable to the
    reference TVD without a separate offset correction."""
    lines = path.read_text(encoding="iso-8859-1", errors="replace").splitlines()
    in_table = False
    rows: list[dict[str, float]] = []
    for line in lines:
        if line.strip().startswith("MD") and "Inc" in line:
            in_table = True
            continue
        if not in_table:
            continue
        if line.strip().startswith("m RKB") or not line.strip():
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        rows.append(
            {
                "md": float(m["md"]),
                "inc_deg": float(m["inc"]),
                "azi_deg": float(m["azi"]),
                "tvd_ref": float(m["tvd"]),
                "east_ref": float(m["x"]),
                "north_ref": float(m["y"]),
            }
        )
    if not rows:
        return pl.DataFrame(
            schema={
                "md": pl.Float64,
                "inc_deg": pl.Float64,
                "azi_deg": pl.Float64,
                "tvd": pl.Float64,
                "north": pl.Float64,
                "east": pl.Float64,
                "tvd_ref": pl.Float64,
                "north_ref": pl.Float64,
                "east_ref": pl.Float64,
            }
        )
    tvd, north, east = minimum_curvature(
        [r["md"] for r in rows], [r["inc_deg"] for r in rows], [r["azi_deg"] for r in rows]
    )
    for r, t, n_, e in zip(rows, tvd, north, east, strict=True):
        r["tvd"] = t + rows[0]["tvd_ref"]  # anchor to the file's own datum TVD, see docstring
        r["north"] = n_ + rows[0]["north_ref"]
        r["east"] = e + rows[0]["east_ref"]
    return pl.DataFrame(rows).select(
        ["md", "inc_deg", "azi_deg", "tvd", "north", "east", "tvd_ref", "north_ref", "east_ref"]
    )


def max_tvd_discrepancy(df: pl.DataFrame) -> float:
    """Max absolute difference between our computed TVD and the archive's own reference TVD —
    the QC check this module's docstring promises. Call this in a test against real data rather
    than trusting the minimum-curvature implementation on faith."""
    if df.is_empty():
        return 0.0
    max_diff = (df["tvd"] - df["tvd_ref"]).abs().max()
    assert isinstance(max_diff, (int, float))
    return float(max_diff)
