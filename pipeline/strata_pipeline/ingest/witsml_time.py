"""Real-time WITSML log ingest -> `time.parquet` — docs/07_DATA_AND_ALGORITHMS.md §2.

docs/DATA_INVENTORY.md recorded the shape this has to handle: a wellbore's real-time data is
spread across dozens of separate named log objects (not one composite feed), the same physical
wellbore can be registered under several operator-prefix folders, and sampling cadence is
irregular within a single log. This module scans every log object across every registration for
a wellbore, keeps only canonical drilling channels (per `mnemonics.yaml`), and merges everything
onto one UTC time axis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import polars as pl
import yaml

from .witsml_common import find_wellbore_dirs, log_data_files, log_objects, log_sets, parse_stripped

_MNEMONICS_PATH = Path(__file__).parent / "mnemonics.yaml"


class UnitConversionError(Exception):
    """Raised when a curve's raw unit has no entry in mnemonics.yaml's unit_conversions table —
    deliberately fatal rather than silently skipping or assuming the value is already canonical
    (CLAUDE.md: "never fabricate data; unknown values are null + a visible placeholder" — a
    wrong unit conversion is worse than a crash, since the value looks plausible either way)."""


@dataclass(frozen=True)
class ChannelSpec:
    canonical_unit: str
    candidates: list[str]


def load_mnemonic_map() -> tuple[dict[str, ChannelSpec], dict[str, float]]:
    raw = yaml.safe_load(_MNEMONICS_PATH.read_text())
    channels = {
        name: ChannelSpec(canonical_unit=spec["canonical_unit"], candidates=spec["candidates"])
        for name, spec in raw["channels"].items()
    }
    return channels, raw["unit_conversions"]


def _convert(value: float, raw_unit: str, canonical_unit: str, conversions: dict[str, float]) -> float:
    if raw_unit == canonical_unit:
        return value
    key = f"{raw_unit}->{canonical_unit}"
    factor = conversions.get(key)
    if factor is None:
        raise UnitConversionError(
            f"no conversion registered for {raw_unit!r} -> {canonical_unit!r} "
            f"(add it to pipeline/strata_pipeline/ingest/mnemonics.yaml)"
        )
    return value * factor


def _parse_log_file(xml_path: Path) -> tuple[int, dict[str, str], list[str], list[list[str]]] | None:
    """Returns (time_column_index, {mnemonic: unit}, mnemonicList, data_rows) for one log XML
    chunk, or None if it's not a time-indexed log (depth-indexed logs are a separate, later
    ingest path — docs/07_DATA_AND_ALGORITHMS.md §2's depth.parquet) or has no usable data.
    `indexCurve` (not an assumed column-0 "Time") says which mnemonicList column is the index —
    confirmed present and always "Time" in the Volve archive, but reading it from the header
    avoids a silent misparse if some log ever orders columns differently."""
    try:
        root = parse_stripped(xml_path)
    except ET.ParseError:
        return None
    log_el = root.find("log")
    if log_el is None:
        return None
    index_type_el = log_el.find("indexType")
    if index_type_el is None or index_type_el.text != "date time":
        return None
    index_curve_el = log_el.find("indexCurve")
    if index_curve_el is None or not index_curve_el.text:
        return None
    index_curve_name = index_curve_el.text

    units: dict[str, str] = {}
    for curve in log_el.findall("logCurveInfo"):
        mnem_el = curve.find("mnemonic")
        unit_el = curve.find("unit")
        if mnem_el is not None and mnem_el.text:
            units[mnem_el.text] = unit_el.text if unit_el is not None and unit_el.text else "unitless"

    log_data = log_el.find("logData")
    if log_data is None:
        return None
    mnem_list_el = log_data.find("mnemonicList")
    if mnem_list_el is None or not mnem_list_el.text:
        return None
    mnemonic_list = mnem_list_el.text.split(",")
    if index_curve_name not in mnemonic_list:
        return None
    time_idx = mnemonic_list.index(index_curve_name)
    rows = [d.text.split(",") if d.text else [] for d in log_data.findall("data")]
    return time_idx, units, mnemonic_list, rows


def _parse_timestamp(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def load_well_time_series(witsml_root: Path, wellbore_name: str) -> pl.DataFrame:
    """All canonical drilling channels for one wellbore, UTC-indexed, long-format rows
    `(t, channel, value_canonical, raw_mnemonic, raw_unit, source_log)` — deliberately NOT
    pre-pivoted/resampled here (that's QC's job, §3: unit fixes, sentinel/spike/frozen-value gap
    detection need the raw per-source rows first). One raw mnemonic can appear in several
    different named logs for the same wellbore; all are kept with their source log recorded so
    QC can reconcile disagreements rather than silently picking one."""
    channels, conversions = load_mnemonic_map()
    mnemonic_to_channel: dict[str, str] = {}
    for canon, spec in channels.items():
        for cand in spec.candidates:
            mnemonic_to_channel.setdefault(cand, canon)

    bore_dirs = find_wellbore_dirs(witsml_root, wellbore_name)
    if not bore_dirs:
        raise FileNotFoundError(f"no WITSML registration found for wellbore {wellbore_name!r} under {witsml_root}")

    records: list[dict[str, Any]] = []
    for bore_dir in bore_dirs:
        for logset in log_sets(bore_dir):
            for logobj in log_objects(logset):
                log_name = logobj.name  # numeric id; MetaFileInfo.txt in the parent has the
                # human name, kept as source_log = f"{logset.name}/{log_name}" for traceability.
                source_log = f"{bore_dir.name}/log/{logset.name}/{log_name}"
                for xml_path in log_data_files(logobj):
                    parsed = _parse_log_file(xml_path)
                    if parsed is None:
                        continue
                    time_idx, units, mnemonic_list, rows = parsed
                    # Which columns in this log's mnemonicList map to a canonical channel we want.
                    wanted = {
                        i: (mnemonic_to_channel[m], m)
                        for i, m in enumerate(mnemonic_list)
                        if m in mnemonic_to_channel
                    }
                    if not wanted:
                        continue
                    for row in rows:
                        if len(row) <= time_idx:
                            continue
                        t = _parse_timestamp(row[time_idx])
                        if t is None:
                            continue
                        for col_idx, (canon, raw_mnem) in wanted.items():
                            if col_idx >= len(row) or not row[col_idx]:
                                continue
                            try:
                                raw_value = float(row[col_idx])
                            except ValueError:
                                continue
                            raw_unit = units.get(raw_mnem, "unitless")
                            canonical_unit = channels[canon].canonical_unit
                            try:
                                value = _convert(raw_value, raw_unit, canonical_unit, conversions)
                            except UnitConversionError:
                                continue
                            records.append(
                                {
                                    "t": t,
                                    "channel": canon,
                                    "value": value,
                                    "raw_mnemonic": raw_mnem,
                                    "raw_unit": raw_unit,
                                    "source_log": source_log,
                                }
                            )

    if not records:
        return pl.DataFrame(
            schema={
                "t": pl.Datetime("ms", "UTC"),
                "channel": pl.Utf8,
                "value": pl.Float64,
                "raw_mnemonic": pl.Utf8,
                "raw_unit": pl.Utf8,
                "source_log": pl.Utf8,
            }
        )
    df = pl.DataFrame(records)
    return df.sort("t")
