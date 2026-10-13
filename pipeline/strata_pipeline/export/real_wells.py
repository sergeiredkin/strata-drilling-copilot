"""The real-data well registry — docs/DATA_INVENTORY.md §2's 6 confirmed wells, with the paths
and names T2.2/T2.3's ingest needs. IDs match `fixtures/wells.py`'s `WellSpec.id` exactly (same
well, two different data sources) so S1's roster doesn't change when real exports replace
fixtures. Raw archive layout documented in docs/DATA_INVENTORY.md §1; never hand-edit paths here
without re-checking that file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_VOLVE_ROOT = REPO_ROOT / "data" / "raw" / "equinor_volve"

WITSML_ROOT = _VOLVE_ROOT / "witsml" / "WITSML Realtime drilling data"
DDR_DIR = (
    _VOLVE_ROOT / "well_technical_data" / "Well_technical_data" / "Daily Drilling Report - XML Version"
)
# Formation tops (ADR 0010) — a separate provenance from the Databricks-sourced archives above,
# so it's its own path rather than nested under `_VOLVE_ROOT`.
WELL_PICKS_CSV = REPO_ROOT / "data" / "raw" / "volve_well_picks" / "Volve_well_picks_modified.csv"


@dataclass(frozen=True)
class RealWellSpec:
    id: str
    wellbore_name: str  # real WITSML <nameWellbore>, resolved to every registration folder by
    # ingest.witsml_common.find_wellbore_dirs — never a hardcoded folder path.
    ddr_file_prefix: str  # archive's underscore-joined well id, e.g. "15_9_F_11_A"
    travelling_block_weight: float = 200.0  # kN, HL_slips fallback input (07 §4) — a generic
    # placeholder until a real per-rig travelling-block weight is sourced; the histogram-valley
    # method (rigstate/calibration.py) is used whenever the data supports it, so this mostly
    # only matters for wells/windows without a real two-population hookload distribution.


REAL_WELLS: list[RealWellSpec] = [
    RealWellSpec(id="15_9-F-11_A", wellbore_name="15/9-F-11 A", ddr_file_prefix="15_9_F_11_A"),
    RealWellSpec(id="15_9-F-15_D", wellbore_name="15/9-F-15 D", ddr_file_prefix="15_9_F_15_D"),
    RealWellSpec(id="15_9-F-14", wellbore_name="15/9-F-14", ddr_file_prefix="15_9_F_14"),
    RealWellSpec(id="15_9-F-12", wellbore_name="15/9-F-12", ddr_file_prefix="15_9_F_12"),
    RealWellSpec(id="15_9-F-5", wellbore_name="15/9-F-5", ddr_file_prefix="15_9_F_5"),
    RealWellSpec(id="15_9-F-1_C", wellbore_name="15/9-F-1 C", ddr_file_prefix="15_9_F_1_C"),
]


def raw_data_available() -> bool:
    """True if the raw Volve archive (T2.1's manual Databricks download) is present on disk.
    `run_well`/`generate_real` should check this before attempting a real run rather than
    failing deep inside XML parsing with a confusing path error."""
    return WITSML_ROOT.is_dir() and DDR_DIR.is_dir()
