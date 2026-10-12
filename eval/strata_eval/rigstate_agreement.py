"""Rig-state gold-sample agreement — docs/07_DATA_AND_ALGORITHMS.md §4 validation step (b): "hand-
labelled gold sample of 200 random 10-min windows in `eval/rigstate_gold.csv` (labelled by Sergei)
-> per-state precision/recall on S5." This module only computes agreement given a gold CSV; it
never generates or guesses labels itself (CLAUDE.md: never fabricate data)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from strata_pipeline.rigstate.intervals import RigStateInterval


@dataclass(frozen=True)
class GoldWindow:
    well: str
    t0: datetime
    t1: datetime
    label: str
    notes: str = ""


@dataclass(frozen=True)
class AgreementReport:
    overall_agreement: float | None  # None if there were no comparable gold windows
    n_compared: int
    n_unlabelled_by_model: int  # gold windows the classifier had zero coverage for
    per_state: dict[str, dict[str, float]]  # state -> {"precision": .., "recall": ..}
    per_well_agreement: dict[str, float | None]


def load_gold(path: Path) -> list[GoldWindow]:
    """Reads `well,t0,t1,label[,notes]` rows. `t0`/`t1` must be ISO-8601 with a UTC offset (Z or
    +00:00) — same convention as the ingest modules, so gold windows line up with model output
    without a separate timezone-fixup step."""
    rows: list[GoldWindow] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                GoldWindow(
                    well=row["well"],
                    t0=datetime.fromisoformat(row["t0"]),
                    t1=datetime.fromisoformat(row["t1"]),
                    label=row["label"],
                    notes=row.get("notes", "") or "",
                )
            )
    return rows


def majority_predicted_state(intervals: list[RigStateInterval], t0: datetime, t1: datetime) -> str | None:
    """The state with the most overlap-seconds against `intervals` inside `[t0, t1]`. None if no
    interval overlaps the window at all (the classifier had no coverage there)."""
    overlap_by_state: dict[str, float] = {}
    for iv in intervals:
        lo = max(iv.t0, t0)
        hi = min(iv.t1, t1)
        overlap = (hi - lo).total_seconds()
        if overlap > 0:
            overlap_by_state[iv.state] = overlap_by_state.get(iv.state, 0.0) + overlap
    if not overlap_by_state:
        return None
    return max(overlap_by_state, key=lambda s: overlap_by_state[s])


def compute_agreement(
    gold: list[GoldWindow], predicted_by_well: dict[str, list[RigStateInterval]]
) -> AgreementReport:
    confusion: dict[tuple[str, str], int] = {}
    per_well_hits: dict[str, list[bool]] = {}
    n_unlabelled = 0

    for window in gold:
        intervals = predicted_by_well.get(window.well, [])
        predicted = majority_predicted_state(intervals, window.t0, window.t1)
        per_well_hits.setdefault(window.well, [])
        if predicted is None:
            n_unlabelled += 1
            continue
        confusion[(window.label, predicted)] = confusion.get((window.label, predicted), 0) + 1
        per_well_hits[window.well].append(predicted == window.label)

    n_compared = sum(confusion.values())
    overall = (sum(v for (t, p), v in confusion.items() if t == p) / n_compared) if n_compared else None

    states = sorted({t for t, _ in confusion} | {p for _, p in confusion})
    per_state: dict[str, dict[str, float]] = {}
    for state in states:
        tp = confusion.get((state, state), 0)
        predicted_as_state = sum(v for (_, p), v in confusion.items() if p == state)
        actual_state = sum(v for (t, _), v in confusion.items() if t == state)
        precision = tp / predicted_as_state if predicted_as_state else 0.0
        recall = tp / actual_state if actual_state else 0.0
        per_state[state] = {"precision": precision, "recall": recall}

    per_well_agreement: dict[str, float | None] = {
        well: (sum(hits) / len(hits) if hits else None) for well, hits in per_well_hits.items()
    }

    return AgreementReport(
        overall_agreement=overall,
        n_compared=n_compared,
        n_unlabelled_by_model=n_unlabelled,
        per_state=per_state,
        per_well_agreement=per_well_agreement,
    )
