"""Formation tops ingest — `data/raw/volve_well_picks/Volve_well_picks_modified.csv`
(docs/DATA_INVENTORY.md §1, docs/LICENSES.md: a third-party redistribution of Equinor's original
2018 Volve well-picks file, used because none of the Databricks-sourced archives or NPD/Sodir's
own public tops layer has per-well tops for these development wells). One row per depth pick
(`WELL,PICKS,...,DEPTH,TVD,...`); `PICKS` names range from group tops ("NORDLAND GP. Top") to
formation and intra-formation sand-body tops/bases ("Hugin Fm. VOLVE Top"/"...Base").

This module only resolves raw picks to one of STRATA's wells and returns them sorted by depth —
turning that into `FormationReport.tops` intervals (deciding what the deepest pick's base is,
how to treat repeated/faulted-repeat picks, which levels to keep) is T11.2's job, done alongside
the classifier that consumes them, not guessed here.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .witsml_common import normalize_wellbore_name


@dataclass(frozen=True)
class FormationPick:
    name: str  # raw PICKS value, e.g. "Hugin Fm. VOLVE Top"
    md: float
    tvd: float | None


def load_well_picks_csv(csv_path: Path) -> list[dict[str, str]]:
    """Every row of the picks CSV as a plain dict (csv.DictReader), unfiltered."""
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def picks_for_wellbore(rows: list[dict[str, str]], wellbore_name: str) -> list[FormationPick]:
    """Rows belonging to `wellbore_name` (matched via the same normalization WITSML registration
    lookup uses — the CSV's "NO 15/9-F-11 A" style names otherwise wouldn't match the wellbore
    names `export/real_wells.py` already uses, e.g. "15/9-F-11 A"), sorted by MD ascending.
    Rows with a missing/unparseable DEPTH are dropped, never guessed."""
    target = normalize_wellbore_name(wellbore_name)
    picks: list[FormationPick] = []
    for row in rows:
        if normalize_wellbore_name(row.get("WELL", "")) != target:
            continue
        depth_raw = row.get("DEPTH", "")
        if not depth_raw:
            continue
        try:
            md = float(depth_raw)
        except ValueError:
            continue
        tvd_raw = row.get("TVD", "")
        tvd = None
        if tvd_raw:
            try:
                tvd = float(tvd_raw)
            except ValueError:
                tvd = None
        picks.append(FormationPick(name=row.get("PICKS", "").strip(), md=md, tvd=tvd))
    return sorted(picks, key=lambda p: p.md)


__all__ = ["FormationPick", "load_well_picks_csv", "picks_for_wellbore"]
