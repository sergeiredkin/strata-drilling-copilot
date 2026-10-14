"""T12.1 DDR event extraction — docs/07_DATA_AND_ALGORITHMS.md §10: "rule lexicon first" over DDR
narratives. The lexicon is exactly the one named there, split into 5 keyword clusters, each
mapped to the `IssueType` it describes; `washout` has no listed keyword and is never produced by
this module (not guessed). Precision is NOT assumed perfect — a bare keyword match like "power
loss problem" will also match the `losses` cluster even though it's not a circulation-losses
event; that's why the spec calls for a manual-review CSV over a 50-event sample before the
model card reports a real precision number (`tasks/BACKLOG.md`'s "Needs Sergei" list), not
something this module can self-certify.

The optional LLM pass and the manual-review step are NOT built here — this module is the rule
-lexicon half only, each extracted `Issue` tagged `extraction: "rule"` so a later LLM/manual pass
is additive, not a silent overwrite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..evidence import EvidenceRegistry

_LEXICON: dict[str, re.Pattern[str]] = {
    "stuck_pipe": re.compile(r"\b(stuck|pipe stuck|work(?:ed)? pipe free|jar(?:red|ring)?)\b", re.I),
    "tight_hole": re.compile(r"\b(overpull|tight)\b", re.I),
    "pack_off": re.compile(r"\bpack(?:ed)? off\b", re.I),
    "losses": re.compile(r"\b(loss(?:es)?|lost circulation|LCM)\b", re.I),
    "kick": re.compile(r"\b(kick|influx|gain)\b", re.I),
}


@dataclass(frozen=True)
class EventCandidate:
    issue_type: str
    matched_text: str


def find_event_candidates(narrative: str) -> list[EventCandidate]:
    """Every lexicon cluster that matches `narrative`, in `_LEXICON`'s fixed order — a single
    narrative can report more than one real event (e.g. "tight hole, worked pipe free")."""
    candidates = []
    for issue_type, pattern in _LEXICON.items():
        m = pattern.search(narrative)
        if m:
            candidates.append(EventCandidate(issue_type=issue_type, matched_text=m.group(0)))
    return candidates


def _formation_for_md(md: float | None, tops: list[dict[str, Any]]) -> str | None:
    if md is None:
        return None
    for top in tops:
        if top["md_top"] <= md < top["md_base"]:
            return str(top["name"])
    return None


def extract_issues(
    well: str,
    ddr_rows: list[dict[str, Any]],
    reg: EvidenceRegistry,
    formations: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """`ddr_rows` are `export/real_well.py:build_ddr_json`'s output (each already has the `id`
    this module references in `ddr_activity_ids` — `ddr_{well}_{i}`, same index order). One
    `Issue` per matched candidate per row; `md`/`formation` come straight from the DDR row's own
    `md_from` (real Volve DDR activities do carry an MD field) and, if `formations` is given, a
    lookup into its tops — `None` for either when the row has no MD, never guessed from
    BITDEPTH-at-event-start (that needs the time-indexed channels, out of this module's scope)."""
    tops = formations["tops"] if formations else []
    issues: list[dict[str, Any]] = []
    for row in ddr_rows:
        candidates = find_event_candidates(row["narrative"] or "")
        for candidate in candidates:
            md = row.get("md_from")
            issue_id = f"issue_{row['id']}_{candidate.issue_type}"
            duration = None
            if row["t0"] is not None and row["t1"] is not None:
                duration = reg.quantity(
                    "events.duration",
                    {"issue": issue_id},
                    (row["t1"] - row["t0"]) / 60_000.0,
                    "min",
                    [{"file": "pipeline:real", "sha256": "n/a"}],
                    1,
                )
            issues.append(
                {
                    "id": issue_id,
                    "well": well,
                    "type": candidate.issue_type,
                    "t0": row["t0"],
                    "t1": row["t1"],
                    "md": md,
                    "formation": _formation_for_md(md, tops),
                    "section": None,
                    "duration": duration,
                    "mud": None,
                    "ddr_activity_ids": [row["id"]],
                    "excerpt": row["narrative"],
                    "report_date": row["report_date"],
                    "extraction": "rule",
                }
            )
    return issues


__all__ = ["EventCandidate", "extract_issues", "find_event_candidates"]
