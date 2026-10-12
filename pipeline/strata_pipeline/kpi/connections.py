"""conn_s2s / conn_w2w — docs/07_DATA_AND_ALGORITHMS.md §5:
"conn_s2s — duration of each R2 connection interval (in slips)."
"conn_w2w — from last sample with WOB > 5 kN on bottom before the connection to first such sample
after it."."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from strata_pipeline.rigstate.intervals import RigStateInterval

_ON_BOTTOM_STATES = {"rotary_drilling", "sliding"}


@dataclass(frozen=True)
class ConnectionKPI:
    t0: datetime
    t1: datetime
    conn_s2s_seconds: float
    conn_w2w_seconds: float | None  # None if no on-bottom WOB>threshold sample was found on
    # either side (e.g. the connection is at the very start/end of the well's data)


def expand_states(intervals: list[RigStateInterval], t: list[datetime]) -> list[str | None]:
    """Reconstructs a per-sample state label from compressed intervals, for callers (like this
    module) that need to walk sample-by-sample. `None` for any `t[i]` outside every interval."""
    out: list[str | None] = [None] * len(t)
    iv_idx = 0
    for i, ti in enumerate(t):
        while iv_idx < len(intervals) and ti > intervals[iv_idx].t1:
            iv_idx += 1
        if iv_idx < len(intervals) and intervals[iv_idx].t0 <= ti <= intervals[iv_idx].t1:
            out[i] = intervals[iv_idx].state
    return out


def compute_connections(
    t: list[datetime],
    wob: list[float | None],
    per_sample_state: list[str | None],
    intervals: list[RigStateInterval],
    wob_threshold_kn: float = 5.0,
) -> list[ConnectionKPI]:
    index_by_t = {ti: i for i, ti in enumerate(t)}
    results: list[ConnectionKPI] = []
    for iv in intervals:
        if iv.state != "connection":
            continue
        conn_s2s = (iv.t1 - iv.t0).total_seconds()

        i0 = index_by_t.get(iv.t0)
        i1 = index_by_t.get(iv.t1)
        t_before = None
        if i0 is not None:
            for j in range(i0 - 1, -1, -1):
                if per_sample_state[j] in _ON_BOTTOM_STATES and (wob[j] or 0) > wob_threshold_kn:
                    t_before = t[j]
                    break
        t_after = None
        if i1 is not None:
            for j in range(i1 + 1, len(t)):
                if per_sample_state[j] in _ON_BOTTOM_STATES and (wob[j] or 0) > wob_threshold_kn:
                    t_after = t[j]
                    break

        conn_w2w = (t_after - t_before).total_seconds() if t_before is not None and t_after is not None else None
        results.append(
            ConnectionKPI(t0=iv.t0, t1=iv.t1, conn_s2s_seconds=conn_s2s, conn_w2w_seconds=conn_w2w)
        )
    return results
