"""Builds `FormationReport` (04_DATA_CONTRACTS.md's `wells/<id>/formations.json`) from a well's
already-computed tops intervals (`formation.labels.tops_to_intervals`) and depth features
(`formation.depth_features.build_depth_features`) — ground-truth tops + per-formation descriptive
stats, no classifier/LOWO involved (that's `FormationPrediction`, a separate file this module
does not write).

`FORMATION_LITHOLOGY` maps formation name -> the schema's `lith` enum using general published
North Sea Viking Graben lithostratigraphy (e.g. NPD's lithostratigraphic lexicon) — a formation's
dominant rock type is regional geological knowledge, not something computed per well, and is
never guessed for a name outside this table (falls back to "other"). Chalk formations (Ekofisk,
Hod) are mapped to "limestone", the closest schema enum value — chalk is a fine-grained limestone,
not a separate category the schema offers."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..confidence import assess
from ..evidence import EvidenceRegistry
from .depth_features import DepthFeatureTable
from .labels import FormationInterval

Lith = str  # one of the schema's lith enum values

FORMATION_LITHOLOGY: dict[str, Lith] = {
    "Utsira Fm.": "sandstone",
    "Ty Fm.": "sandstone",
    "Ekofisk Fm.": "limestone",  # chalk
    "Hod Fm.": "limestone",  # chalk
    "Draupne Fm.": "shale",
    "Heather Fm.": "shale",
    "Heather Fm. Sand VOLVE": "sandstone",
    "Hugin Fm. VOLVE": "sandstone",
    "Sleipner Fm.": "sandstone",
    "Skagerrak Fm.": "sandstone",
    "Smith Bank Fm.": "shale",
}


def lith_for_formation(name: str) -> Lith:
    return FORMATION_LITHOLOGY.get(name, "other")


def build_formation_report(
    well: str,
    table: DepthFeatureTable,
    tops: list[FormationInterval],
    reg: EvidenceRegistry,
    source: str,
) -> dict[str, Any]:
    """`source` is the file `tops` came from (recorded in each top's `source` field for
    provenance — `04_DATA_CONTRACTS.md` §6's evidence rule applied to tops, not just Quantities)."""
    src = [{"file": source, "sha256": "n/a"}]
    tops_payload = [
        {"name": iv.name, "md_top": iv.md_top, "md_base": iv.md_base, "source": source} for iv in tops
    ]
    lithology_payload = [
        {"md_top": iv.md_top, "md_base": iv.md_base, "lith": lith_for_formation(iv.name)} for iv in tops
    ]

    stats: list[dict[str, Any]] = []
    for iv in tops:
        in_formation = (table.md >= iv.md_top) & (table.md < iv.md_base)
        n = int(np.sum(in_formation))
        rop_vals = table.rop_m_per_h[in_formation]
        mse_vals = table.mse_mpa[in_formation]
        rop_finite = rop_vals[np.isfinite(rop_vals)]
        mse_finite = mse_vals[np.isfinite(mse_vals)]

        avg_rop = reg.quantity(
            "formation.stats",
            {"well": well, "formation": iv.name, "stat": "avg_rop"},
            float(rop_finite.mean()) if rop_finite.size else None,
            "m/h",
            src,
            2,
        )
        avg_mse = reg.quantity(
            "formation.stats",
            {"well": well, "formation": iv.name, "stat": "avg_mse"},
            float(mse_finite.mean()) if mse_finite.size else None,
            "MPa",
            src,
            2,
        )
        stats.append(
            {
                "formation": iv.name,
                "avg_rop": avg_rop,
                "avg_mse": avg_mse,
                "incidents": 0,  # DDR event extraction (T12.1) isn't built yet -- honestly 0,
                # not a guessed count.
                "n_wells": 1,
                "best_window": None,  # no offset-well parameter-window analysis yet (T11.4).
                "confidence": assess(sample_size=n),
            }
        )

    return {"well": well, "tops": tops_payload, "lithology": lithology_payload, "stats": stats}


__all__ = ["FORMATION_LITHOLOGY", "build_formation_report", "lith_for_formation"]
