"""Turns raw formation picks (`ingest/formation_tops.py`) into depth intervals and labels
T11.1's 1 m MD bins with them — the training labels T11.2's classifier needs (docs/07
§9: "Label: formation from picked tops").

A pick's name is kept as a label only when it marks a *formation* top ("... Fm. Top", including
intra-formation sand-body tops like "Hugin Fm. VOLVE Top") — group tops ("... GP. Top") and
"Seabed" are stratigraphic markers, not formations, and "... Base" rows mark an explicit base
for an intra-formation sand body rather than a new unit's top, so they're not double-counted as
separate intervals (the *next* top in depth order already supplies that boundary). The deepest
pick in a well has no known base (we don't have the well's TD here) and is dropped rather than
guessed — one well's shallowest coverage gap, not a label for every bin to the bottom of the hole."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from ..ingest.formation_tops import FormationPick

_TOP_SUFFIX_RE = re.compile(r"\s+Top(\s*\(\d+\))?\s*$")


@dataclass(frozen=True)
class FormationInterval:
    name: str
    md_top: float
    md_base: float


def _is_formation_top(name: str) -> bool:
    # Matches "... Fm. Top", "... Fm. Top (1)", etc.; excludes "... Fm. Base" and group/seabed
    # markers, which aren't formation tops.
    return "Fm." in name and "Top" in name and "Base" not in name


def _formation_name(pick_name: str) -> str:
    """Strips the "Top"/"Top (n)" suffix a pick name carries (e.g. "Ty Fm. Top" -> "Ty Fm.") so
    the label is the formation's own name, not the pick-event description — the same formation
    repeated at a different depth (a faulted repeat section) must produce the same label."""
    return _TOP_SUFFIX_RE.sub("", pick_name).strip()


def tops_to_intervals(picks: list[FormationPick]) -> list[FormationInterval]:
    """`picks` need not be pre-sorted. Consecutive formation tops in depth order define each
    interval's `[md_top, md_base)`; duplicate-depth picks (zero-width intervals) are dropped."""
    tops = sorted((p for p in picks if _is_formation_top(p.name)), key=lambda p: p.md)
    intervals: list[FormationInterval] = []
    for i, pick in enumerate(tops[:-1]):
        base = tops[i + 1].md
        if base <= pick.md:
            continue
        intervals.append(FormationInterval(name=_formation_name(pick.name), md_top=pick.md, md_base=base))
    return intervals


def label_bins(md: np.ndarray, intervals: list[FormationInterval]) -> np.ndarray:
    """One label per MD bin (`dtype=object`, `str | None`), via the same `[md_top, md_base)`
    lookup `depth_features.bit_diameter_by_md` uses for bit diameter. `None` where no interval
    covers that depth."""
    out = np.full(len(md), None, dtype=object)
    for iv in intervals:
        out[(md >= iv.md_top) & (md < iv.md_base)] = iv.name
    return out


__all__ = ["FormationInterval", "label_bins", "tops_to_intervals"]
