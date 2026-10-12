"""Interval building — docs/07_DATA_AND_ALGORITHMS.md §4 post-processing: "merge intervals < 10 s
into neighbours (hysteresis), except connection" — and interval confidence: "share of samples
whose deciding inputs are > 10% away from thresholds."."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .rules import Decision, RuleResult

_EPS = 1e-9


@dataclass
class RigStateInterval:
    t0: datetime
    t1: datetime
    state: str
    rule_id: str
    confidence: float
    back_reaming: bool
    n_samples: int


@dataclass
class _Segment:
    lo: int
    hi: int  # inclusive
    state: str
    rule_id: str


def _segment_decisive(results: list[RuleResult], margin_frac: float) -> list[bool]:
    out = []
    for r in results:
        out.append(_is_decisive(r, margin_frac))
    return out


def _is_decisive(result: RuleResult, margin_frac: float) -> bool:
    if not result.deciding:
        return False
    margins = [_relative_margin(d) for d in result.deciding]
    return min(margins) > margin_frac


def _relative_margin(d: Decision) -> float:
    return abs(d.value - d.threshold) / max(abs(d.threshold), _EPS)


def _raw_segments(results: list[RuleResult]) -> list[_Segment]:
    segments: list[_Segment] = []
    lo = 0
    for i in range(1, len(results) + 1):
        if i < len(results) and results[i].state == results[lo].state:
            continue
        segments.append(_Segment(lo=lo, hi=i - 1, state=results[lo].state, rule_id=results[lo].rule_id))
        lo = i
    return segments


def _merge_short_segments(
    segments: list[_Segment], t: list[datetime], min_seconds: float
) -> list[_Segment]:
    """Merges a segment shorter than `min_seconds` into its previous neighbour (or, if it is the
    first segment, into the next one) — except `connection` segments, which are always kept.
    Repeats until no more merges happen (a merge can shrink the resulting boundary and leave a
    newly-short neighbour, though in practice one pass is enough since merging only grows
    segments)."""
    segs = list(segments)
    changed = True
    while changed:
        changed = False
        merged: list[_Segment] = []
        i = 0
        while i < len(segs):
            seg = segs[i]
            duration = (t[seg.hi] - t[seg.lo]).total_seconds()
            if seg.state != "connection" and duration < min_seconds and len(segs) > 1:
                if merged:
                    prev = merged.pop()
                    merged.append(_Segment(lo=prev.lo, hi=seg.hi, state=prev.state, rule_id=prev.rule_id))
                elif i + 1 < len(segs):
                    nxt = segs[i + 1]
                    merged.append(_Segment(lo=seg.lo, hi=nxt.hi, state=nxt.state, rule_id=nxt.rule_id))
                    i += 1
                else:
                    merged.append(seg)
                changed = True
            else:
                merged.append(seg)
            i += 1
        segs = merged
    return _coalesce_adjacent(segs)


def _coalesce_adjacent(segs: list[_Segment]) -> list[_Segment]:
    """A merge can leave two adjacent segments with the same final state (the short blip's
    state disappears into a neighbour that then matches the segment on its other side) —
    collapse those back into one interval."""
    if not segs:
        return segs
    out = [segs[0]]
    for seg in segs[1:]:
        if seg.state == out[-1].state:
            out[-1] = _Segment(lo=out[-1].lo, hi=seg.hi, state=out[-1].state, rule_id=out[-1].rule_id)
        else:
            out.append(seg)
    return out


def build_intervals(
    t: list[datetime], results: list[RuleResult], min_interval_seconds: float, margin_frac: float
) -> list[RigStateInterval]:
    if not results:
        return []
    raw = _raw_segments(results)
    merged = _merge_short_segments(raw, t, min_interval_seconds)
    decisive = _segment_decisive(results, margin_frac)

    intervals: list[RigStateInterval] = []
    for seg in merged:
        n = seg.hi - seg.lo + 1
        n_decisive = sum(decisive[seg.lo : seg.hi + 1])
        back_reaming = any(results[i].back_reaming for i in range(seg.lo, seg.hi + 1))
        intervals.append(
            RigStateInterval(
                t0=t[seg.lo],
                t1=t[seg.hi],
                state=seg.state,
                rule_id=seg.rule_id,
                confidence=n_decisive / n if n else 0.0,
                back_reaming=back_reaming,
                n_samples=n,
            )
        )
    return intervals
