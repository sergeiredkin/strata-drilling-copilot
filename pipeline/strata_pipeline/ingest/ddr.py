"""Daily Drilling Report ingest -> `ddr.parquet` — docs/07_DATA_AND_ALGORITHMS.md §2.

docs/DATA_INVENTORY.md: DDR XML timestamps are Norway local time (+01:00/+02:00), unlike the
real-time WITSML logs (UTC) — this module converts to UTC on the way in so ddr.parquet and
time.parquet are directly comparable without the caller having to remember the offset.
"""

from __future__ import annotations

import glob
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from ..recon.ddr_codes import load_ddr_code_rules
from ..recon.ddr_codes import normalize_code as _normalize_code
from .witsml_common import parse_stripped

# Loaded once at import time; recon/ddr_codes.yaml is the single source of truth for this
# mapping, shared with recon/reconciliation.py (docs/07_DATA_AND_ALGORITHMS.md §7).
_CODE_RULES = load_ddr_code_rules()


def normalize_code(raw_code: str) -> str:
    """Maps a raw Volve `proprietaryCode` to one of DRILL/CIRC/TRIP/REAM/CASING/CEMENT/BOP/WAIT/
    OTHER (`recon/ddr_codes.yaml`). Falls back to OTHER for anything not explicitly matched
    (completion, workover, plug abandon other than cementing, formation evaluation, etc.) rather
    than guessing — those aren't drilling-phase activity and the reconciliation module only
    defines expected sensor states for DRILL/CIRC/TRIP/REAM anyway."""
    return _normalize_code(raw_code, _CODE_RULES)


def _parse_local_datetime(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def parse_ddr_file(xml_path: Path) -> list[dict[str, Any]]:
    """One row per `<activity>` in a single day's DDR XML, timestamps converted to UTC."""
    root = parse_stripped(xml_path)
    report_el = root.find("drillReport")
    if report_el is None:
        return []
    well_name_el = report_el.find("nameWell")
    wellbore_name_el = report_el.find("nameWellbore")
    well_name = well_name_el.text if well_name_el is not None else None
    wellbore_name = wellbore_name_el.text if wellbore_name_el is not None else None
    dtim_start_el = report_el.find("dTimStart")
    report_date = None
    if dtim_start_el is not None and dtim_start_el.text:
        dt = _parse_local_datetime(dtim_start_el.text)
        if dt is not None:
            report_date = dt.date().isoformat()

    rows: list[dict[str, Any]] = []
    for activity in report_el.findall("activity"):
        t0_el = activity.find("dTimStart")
        t1_el = activity.find("dTimEnd")
        md_el = activity.find("md")
        code_el = activity.find("proprietaryCode")
        state_el = activity.find("state")
        comments_el = activity.find("comments")
        t0 = _parse_local_datetime(t0_el.text) if t0_el is not None and t0_el.text else None
        t1 = _parse_local_datetime(t1_el.text) if t1_el is not None and t1_el.text else None
        if t0 is None or t1 is None:
            continue
        raw_code = code_el.text if code_el is not None and code_el.text else "unknown -- unknown"
        rows.append(
            {
                "well": well_name,
                "wellbore": wellbore_name,
                "report_date": report_date,
                "t0": t0.astimezone(UTC),
                "t1": t1.astimezone(UTC),
                "md": float(md_el.text) if md_el is not None and md_el.text else None,
                "raw_code": raw_code,
                "normalized_code": normalize_code(raw_code),
                "state": state_el.text if state_el is not None else None,
                "narrative": re.sub(r"\s+", " ", comments_el.text).strip()
                if comments_el is not None and comments_el.text
                else "",
            }
        )
    return rows


def load_well_ddr(ddr_dir: Path, well_file_prefix: str) -> pl.DataFrame:
    """All activity rows across every `<well_file_prefix>_*.xml` daily report in `ddr_dir`
    (docs/DATA_INVENTORY.md's "Daily Drilling Report - XML Version" folder), sorted by t0.
    `well_file_prefix` is the archive's underscore-joined well id, e.g. "15_9_F_11_A"."""
    files = sorted(glob.glob(str(ddr_dir / f"{well_file_prefix}_*.xml")))
    rows: list[dict[str, Any]] = []
    for f in files:
        rows.extend(parse_ddr_file(Path(f)))
    if not rows:
        return pl.DataFrame(
            schema={
                "well": pl.Utf8,
                "wellbore": pl.Utf8,
                "report_date": pl.Utf8,
                "t0": pl.Datetime("us", "UTC"),
                "t1": pl.Datetime("us", "UTC"),
                "md": pl.Float64,
                "raw_code": pl.Utf8,
                "normalized_code": pl.Utf8,
                "state": pl.Utf8,
                "narrative": pl.Utf8,
            }
        )
    df = pl.DataFrame(rows)
    return df.sort("t0")
