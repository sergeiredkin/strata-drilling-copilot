"""Copilot tools — docs/07_DATA_AND_ALGORITHMS.md §12. Every tool is a thin, read-only wrapper
over the same static export the HTTP routes serve (docs/03_ARCHITECTURE.md §4: "tools are thin
wrappers over export tables/evidence (no free SQL)") — no tool recomputes analytics. Most tools
pass through a `Quantity` that already carries a real `evidence_id` from the static export
unchanged; `rigstate_summary` is the one exception (an arbitrary caller-chosen time window the
pipeline never pre-aggregated) and mints a fresh evidence record through the session's own
`EvidenceRegistry` instead — see docs/adr/0008-copilot-tool-signatures.md for why, and for the
`kpi_connection_times`/`kpi_trips` shape choice.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from strata_pipeline.evidence import EvidenceRegistry

from ..data_access import read_json, read_json_or_default
from ..settings import Settings

_WORD_RE = re.compile(r"[a-z0-9]+")


class ToolError(Exception):
    """Raised by a tool handler for an expected, user-legible failure (unknown well, unknown
    section, missing export file). Caught by the agent loop and returned to the model as a tool
    error result — never a 500, since a wrong tool argument is the model's mistake to recover
    from, not a crash."""


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _bm25_search(corpus: list[str], query: str, top_k: int) -> list[tuple[int, float]]:
    """Minimal BM25 (k1=1.5, b=0.75) over `corpus` (one short DDR narrative per row) — a real
    library wasn't worth adding as a dependency for scoring a few hundred short strings per well.
    Returns (index, score) pairs for the `top_k` highest-scoring non-zero matches, scores
    descending."""
    k1, b = 1.5, 0.75
    docs = [_tokenize(doc) for doc in corpus]
    doc_lens = [len(d) for d in docs]
    avg_len = sum(doc_lens) / len(doc_lens) if doc_lens else 0.0
    n_docs = len(docs)

    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))

    query_terms = _tokenize(query)
    scores = [0.0] * n_docs
    for term in query_terms:
        n_t = df.get(term, 0)
        if n_t == 0:
            continue
        idf = math.log((n_docs - n_t + 0.5) / (n_t + 0.5) + 1)
        for i, doc in enumerate(docs):
            f = doc.count(term)
            if f == 0:
                continue
            denom = f + k1 * (1 - b + b * (doc_lens[i] / avg_len if avg_len else 0))
            scores[i] += idf * (f * (k1 + 1)) / denom

    ranked = sorted(((i, s) for i, s in enumerate(scores) if s > 0), key=lambda pair: pair[1], reverse=True)
    return ranked[:top_k]


def _require_well_dir(settings: Settings, well: str) -> None:
    if not (settings.data_dir / "wells" / well).is_dir():
        raise ToolError(f"unknown well id: {well!r}")


def _find_well_summary(settings: Settings, well: str) -> dict[str, Any]:
    wells: list[dict[str, Any]] = read_json(settings, "wells.json")["wells"]
    for w in wells:
        if w["id"] == well:
            return w
    raise ToolError(f"unknown well id: {well!r}")


class CopilotTools:
    """Bound to one `/ask` request: `settings` for reading the static export, `reg` the
    request-scoped `EvidenceRegistry` for any tool that mints a new evidence record (see module
    docstring)."""

    def __init__(self, settings: Settings, reg: EvidenceRegistry) -> None:
        self.settings = settings
        self.reg = reg

    def list_wells(self) -> dict[str, Any]:
        return {"wells": read_json(self.settings, "wells.json")["wells"]}

    def well_summary(self, well: str) -> dict[str, Any]:
        return _find_well_summary(self.settings, well)

    def rigstate_summary(self, well: str, t0: float, t1: float) -> dict[str, Any]:
        _require_well_dir(self.settings, well)
        rows = read_json(self.settings, f"wells/{well}/rigstate.json")
        in_window = [r for r in rows if r["t1"] > t0 and r["t0"] < t1]
        by_state_seconds: dict[str, float] = {}
        for r in in_window:
            overlap_t0, overlap_t1 = max(r["t0"], t0), min(r["t1"], t1)
            seconds = max(0.0, (overlap_t1 - overlap_t0) / 1000.0)
            by_state_seconds[r["state"]] = by_state_seconds.get(r["state"], 0.0) + seconds
        by_state = {
            state: self.reg.quantity(
                "copilot.rigstate_summary",
                {"well": well, "state": state, "t0": t0, "t1": t1},
                seconds / 3600.0,
                "h",
                [{"file": f"wells/{well}/rigstate.json"}],
                2,
            )
            for state, seconds in by_state_seconds.items()
        }
        return {"well": well, "t0": t0, "t1": t1, "n_intervals": len(in_window), "by_state": by_state}

    def kpi_connection_times(self, well: str, section: str, stat: str) -> dict[str, Any]:
        if stat not in ("s2s", "w2w"):
            raise ToolError(f"stat must be 's2s' or 'w2w', got {stat!r}")
        return self._kpi_lookup(well, section, f"conn_{stat}")

    def kpi_trips(self, well: str, section: str, direction: str, hole: str) -> dict[str, Any]:
        if direction not in ("in", "out"):
            raise ToolError(f"direction must be 'in' or 'out', got {direction!r}")
        if hole not in ("cased", "open"):
            raise ToolError(f"hole must be 'cased' or 'open', got {hole!r}")
        return self._kpi_lookup(well, section, f"trip_{direction}_{hole}")

    def _kpi_lookup(self, well: str, section: str, kpi: str) -> dict[str, Any]:
        _require_well_dir(self.settings, well)
        report = read_json(self.settings, f"wells/{well}/kpis.json")
        if section == "well":
            card = next((c for c in report["cards"] if c["kpi"] == kpi), None)
            if card is None:
                raise ToolError(f"well {well!r} has no kpi {kpi!r}")
            return {"well": well, "kpi": kpi, "section": "well", "value": card["value"], "best": card["best"]}
        dist = next(
            (d for d in report["distributions"] if d["kpi"] == kpi and d["section"] == section), None
        )
        if dist is None:
            raise ToolError(f"well {well!r} has no kpi {kpi!r} for section {section!r}")
        return {"well": well, "kpi": kpi, "section": section, "dist": dist["dist"]}

    def ilt_breakdown(self, well: str, by: str) -> dict[str, Any]:
        if by not in ("category", "section", "day"):
            raise ToolError(f"by must be 'category', 'section' or 'day', got {by!r}")
        _require_well_dir(self.settings, well)
        report = read_json(self.settings, f"wells/{well}/ilt.json")
        key = {"category": "by_category", "section": "by_section", "day": "by_day"}[by]
        return {
            "well": well,
            "total": report["total"],
            "booked_npt": report["booked_npt"],
            "excluded_gap_hours": report["excluded_gap_hours"],
            by: report[key],
        }

    def reconciliation(self, well: str | None = None) -> dict[str, Any]:
        path = f"reconciliation/{well}.json" if well else "reconciliation/all.json"
        if well is not None:
            _require_well_dir(self.settings, well)
        return read_json(self.settings, path)  # type: ignore[no-any-return]

    def mismatches(self, well: str, t0: float | None = None, t1: float | None = None) -> dict[str, Any]:
        _require_well_dir(self.settings, well)
        rows = read_json(self.settings, f"wells/{well}/mismatches.json")
        if t0 is not None and t1 is not None:
            rows = [r for r in rows if r["t1"] > t0 and r["t0"] < t1]
        return {"well": well, "mismatches": rows}

    def ddr_search(
        self, well: str, query: str, t0: float | None = None, t1: float | None = None, top_k: int = 5
    ) -> dict[str, Any]:
        _require_well_dir(self.settings, well)
        rows = read_json(self.settings, f"wells/{well}/ddr.json")
        if t0 is not None and t1 is not None:
            rows = [r for r in rows if r["t1"] > t0 and r["t0"] < t1]
        ranked = _bm25_search([r["narrative"] for r in rows], query, top_k)
        results = [
            {
                "id": rows[i]["id"],
                "t0": rows[i]["t0"],
                "t1": rows[i]["t1"],
                "narrative": rows[i]["narrative"],
                "score": score,
            }
            for i, score in ranked
        ]
        return {"well": well, "query": query, "results": results}

    def formation_stats(self, well: str, formation: str) -> dict[str, Any]:
        _require_well_dir(self.settings, well)
        report = read_json_or_default(self.settings, f"wells/{well}/formations.json", None)
        if report is None:
            raise ToolError(f"no formation data exported for well {well!r} yet")
        stat = next((s for s in report["stats"] if s["formation"] == formation), None)
        if stat is None:
            raise ToolError(f"well {well!r} has no stats for formation {formation!r}")
        return stat  # type: ignore[no-any-return]

    def issues_query(
        self, well: str | None = None, type: str | None = None, formation: str | None = None  # noqa: A002
    ) -> dict[str, Any]:
        rows = read_json_or_default(self.settings, "issues.json", [])
        if well is not None:
            rows = [r for r in rows if r.get("well") == well]
        if type is not None:
            rows = [r for r in rows if r.get("type") == type]
        if formation is not None:
            rows = [r for r in rows if r.get("formation") == formation]
        return {"issues": rows}

    def evidence(self, id: str) -> dict[str, Any]:  # noqa: A002 - matches the contract's field name
        try:
            return self.reg.get(id)
        except KeyError:
            pass
        shard_of = read_json_or_default(self.settings, "evidence/shards.json", {})
        shard = shard_of.get(id)
        if shard is None:
            raise ToolError(f"unknown evidence id: {id!r}")
        shard_records = read_json(self.settings, f"evidence/{shard}.json")
        record = shard_records.get(id)
        if record is None:
            raise ToolError(f"unknown evidence id: {id!r}")
        return record  # type: ignore[no-any-return]


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "list_wells",
        "description": "List every well in the export with id, name, field, years and sections.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "well_summary",
        "description": "Full summary (coverage, depth range, sections) for one well.",
        "input_schema": {
            "type": "object",
            "properties": {"well": {"type": "string"}},
            "required": ["well"],
        },
    },
    {
        "name": "rigstate_summary",
        "description": (
            "Total hours per rig state inside an arbitrary [t0, t1) window (epoch ms). Use this "
            "for 'how much time was spent X' questions over a specific window."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "t0": {"type": "number", "description": "epoch ms"},
                "t1": {"type": "number", "description": "epoch ms"},
            },
            "required": ["well", "t0", "t1"],
        },
    },
    {
        "name": "kpi_connection_times",
        "description": (
            "Connection-time distribution (slips-to-slips or weight-to-weight) for one well and "
            "section ('well' for the well-level figure, otherwise a hole-size section name)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "section": {"type": "string"},
                "stat": {"type": "string", "enum": ["s2s", "w2w"]},
            },
            "required": ["well", "section", "stat"],
        },
    },
    {
        "name": "kpi_trips",
        "description": (
            "Trip-speed distribution for one well and section ('well' for the well-level figure, "
            "otherwise a hole-size section name), by direction and hole type."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "section": {"type": "string"},
                "direction": {"type": "string", "enum": ["in", "out"]},
                "hole": {"type": "string", "enum": ["cased", "open"]},
            },
            "required": ["well", "section", "direction", "hole"],
        },
    },
    {
        "name": "ilt_breakdown",
        "description": "Invisible lost time, broken down by category, section or day.",
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "by": {"type": "string", "enum": ["category", "section", "day"]},
            },
            "required": ["well", "by"],
        },
    },
    {
        "name": "reconciliation",
        "description": "DDR-vs-sensor rig-state agreement table for one well, or every well if omitted.",
        "input_schema": {
            "type": "object",
            "properties": {"well": {"type": "string"}},
        },
    },
    {
        "name": "mismatches",
        "description": "DDR-vs-sensor disagreement intervals for one well, optionally windowed by [t0, t1) epoch ms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "t0": {"type": "number"},
                "t1": {"type": "number"},
            },
            "required": ["well"],
        },
    },
    {
        "name": "ddr_search",
        "description": "Full-text search over one well's daily-report narratives; returns matching row ids and text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "query": {"type": "string"},
                "t0": {"type": "number"},
                "t1": {"type": "number"},
                "top_k": {"type": "integer"},
            },
            "required": ["well", "query"],
        },
    },
    {
        "name": "formation_stats",
        "description": "Offset-well ROP/MSE/incident stats for one formation (may be unavailable for a well).",
        "input_schema": {
            "type": "object",
            "properties": {"well": {"type": "string"}, "formation": {"type": "string"}},
            "required": ["well", "formation"],
        },
    },
    {
        "name": "issues_query",
        "description": "Search the issue catalogue by well, type and/or formation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "well": {"type": "string"},
                "type": {"type": "string"},
                "formation": {"type": "string"},
            },
        },
    },
    {
        "name": "evidence",
        "description": "Look up one evidence record by id (resolves ids minted this session too).",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]

# submit_answer's schema is CopilotAnswer's own JSON schema, assembled in agent.py (it needs the
# generated pydantic model, which this module deliberately doesn't import to stay a pure,
# easily-unit-testable "data access" layer).
__all__ = ["CopilotTools", "ToolError", "TOOL_SPECS"]
