"""DDR reconciliation — docs/07_DATA_AND_ALGORITHMS.md §7: booked DDR activity code vs. measured
rig state. Produces the `Reconciliation` contract shape
(`contracts/schemas/strata.schema.json`): a code x rig-state minutes/pct matrix, per-code
agreement, and a minute-weighted per-well agreement over the codes that have an expected state
set (DRILL/CIRC/TRIP/REAM — CASING/CEMENT/BOP/WAIT/OTHER are excluded from agreement, not scored
as always-wrong)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from strata_pipeline.rigstate.intervals import RigStateInterval

RIG_STATES = (
    "rotary_drilling",
    "sliding",
    "connection",
    "trip_in",
    "trip_out",
    "reaming",
    "circulating",
    "out_of_hole",
    "unknown",
)


@dataclass(frozen=True)
class DdrRow:
    t0: datetime
    t1: datetime
    normalized_code: str


@dataclass(frozen=True)
class Cell:
    minutes: float
    pct: float


@dataclass(frozen=True)
class CodeAgreement:
    code: str
    pct: float | None  # None if the code has zero outside-slack minutes anywhere
    booked_minutes: float


@dataclass(frozen=True)
class ReconciliationResult:
    rows: list[str]
    cols: tuple[str, ...]
    cells: dict[str, dict[str, Cell]]  # cells[code][state]
    agreement: list[CodeAgreement]
    per_well_agreement: float | None


@dataclass(frozen=True)
class MismatchRun:
    code: str
    t0: datetime
    t1: datetime
    state: str


def apply_boundary_slack(t0: datetime, t1: datetime, slack_min: float) -> tuple[datetime, datetime] | None:
    """Trims `slack_min` off each end of a DDR row's window; None if nothing is left (a row
    shorter than twice the slack)."""
    slack = timedelta(minutes=slack_min)
    trimmed_t0, trimmed_t1 = t0 + slack, t1 - slack
    if trimmed_t0 >= trimmed_t1:
        return None
    return trimmed_t0, trimmed_t1


def measured_minutes_by_state(
    intervals: list[RigStateInterval], t0: datetime, t1: datetime
) -> dict[str, float]:
    """Overlap-seconds, in minutes, between `[t0, t1]` and every rig-state interval, keyed by
    `RigStateInterval.state` (so a gap interval's `"unknown"` is counted the same as a true R10
    idle `"unknown"` — the matrix cell is about measured state, not about the classifier's
    certainty)."""
    out: dict[str, float] = {}
    for iv in intervals:
        lo, hi = max(iv.t0, t0), min(iv.t1, t1)
        overlap_s = (hi - lo).total_seconds()
        if overlap_s > 0:
            out[iv.state] = out.get(iv.state, 0.0) + overlap_s / 60.0
    return out


def find_mismatch_runs(
    intervals: list[RigStateInterval],
    ddr_row: DdrRow,
    expected_states: set[str],
    slack_min: float,
    min_duration_min: float,
) -> list[MismatchRun]:
    """Contiguous stretches (>= `min_duration_min`) of a rig state outside `expected_states`,
    inside the slack-trimmed DDR row window. Interval boundaries not aligned with the row window
    are clipped to it."""
    trimmed = apply_boundary_slack(ddr_row.t0, ddr_row.t1, slack_min)
    if trimmed is None:
        return []
    t0, t1 = trimmed
    runs: list[MismatchRun] = []
    for iv in sorted(intervals, key=lambda i: i.t0):
        lo, hi = max(iv.t0, t0), min(iv.t1, t1)
        if hi <= lo:
            continue
        if iv.state in expected_states:
            continue
        duration_min = (hi - lo).total_seconds() / 60.0
        if duration_min >= min_duration_min:
            runs.append(MismatchRun(code=ddr_row.normalized_code, t0=lo, t1=hi, state=iv.state))
    return runs


def compute_reconciliation(
    ddr_rows: list[DdrRow],
    intervals: list[RigStateInterval],
    expected_states: dict[str, list[str]],
    included_codes: list[str],
    boundary_slack_min: float,
) -> ReconciliationResult:
    cells: dict[str, dict[str, Cell]] = {}
    agreement: list[CodeAgreement] = []
    weighted_sum = 0.0
    weighted_n = 0.0

    for code in included_codes:
        rows_for_code = [r for r in ddr_rows if r.normalized_code == code]
        # "booked" intentionally uses each row's full, un-trimmed duration (unlike every other
        # sum in this function) — it means what the DDR actually logged, not what reconciliation
        # chose to look at after applying boundary slack.
        booked_minutes = sum((r.t1 - r.t0).total_seconds() / 60.0 for r in rows_for_code)
        minutes_by_state: dict[str, float] = {}
        for row in rows_for_code:
            trimmed = apply_boundary_slack(row.t0, row.t1, boundary_slack_min)
            if trimmed is None:
                continue
            for state, minutes in measured_minutes_by_state(intervals, *trimmed).items():
                minutes_by_state[state] = minutes_by_state.get(state, 0.0) + minutes

        total_outside_slack = sum(minutes_by_state.values())
        cells[code] = {
            state: Cell(
                minutes=minutes_by_state.get(state, 0.0),
                pct=(minutes_by_state.get(state, 0.0) / total_outside_slack * 100.0) if total_outside_slack else 0.0,
            )
            for state in RIG_STATES
        }

        expected = set(expected_states.get(code, []))
        matched_minutes = sum(m for s, m in minutes_by_state.items() if s in expected)
        pct = (matched_minutes / total_outside_slack * 100.0) if total_outside_slack else None
        agreement.append(CodeAgreement(code=code, pct=pct, booked_minutes=booked_minutes))
        if pct is not None:
            weighted_sum += pct * total_outside_slack
            weighted_n += total_outside_slack

    per_well = weighted_sum / weighted_n if weighted_n else None
    return ReconciliationResult(
        rows=included_codes,
        cols=RIG_STATES,
        cells=cells,
        agreement=agreement,
        per_well_agreement=per_well,
    )
