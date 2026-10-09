"""T1.2 fixture generator entry point — `make fixtures` runs `python -m strata_pipeline.fixtures.generate`.

Writes the full static-mode export (`04_DATA_CONTRACTS.md` §3) into `apps/web/public/data/`:
wells.json, repro.json, eval.json, issues.json, reconciliation/*, evidence/*, copilot/sessions/*,
and per detailed well: sections/depthtime/rigstate/ddr/mismatches/kpis/ilt + the series pyramid.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..evidence import EvidenceRegistry
from ..export.series import export_channel_series
from .kpi import compute_ilt, compute_kpis, compute_mismatches, compute_reconciliation
from .synth import WellDetail, synthesize_well
from .wells import COVERAGE_KINDS, WELLS, WellSpec

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "apps" / "web" / "public" / "data"

_SIZE_IN_MAP = {"26": 26.0, "17½": 17.5, "12¼": 12.25, "8½": 8.5, "8¾": 8.75}


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def well_summary(spec: WellSpec, reg: EvidenceRegistry) -> dict[str, Any]:
    coverage: list[dict[str, Any]] = []
    status_map = {"f": "full", "p": "partial", "n": "none"}
    for kind, code in zip(COVERAGE_KINDS, spec.coverage_codes, strict=True):
        coverage.append({
            "kind": kind, "status": status_map[code], "rows": None, "span": None, "source_files": [],
        })
    source = [{"file": "fixtures/wells.py", "sha256": "mock-fixture"}]
    qc_q = reg.quantity("qc.score", {"well": spec.id}, spec.qc_score, "1", source, 2)
    reasons = {
        "high": "coverage of all 6 data types is full or near-full with few gaps.",
        "medium": "some data types are partial, which reduces certainty.",
        "low": "multiple data types are partial or missing.",
    }
    return {
        "id": spec.id,
        "name": spec.name,
        "field": spec.field,
        "years": spec.years,
        "md_range": list(spec.md_range),
        "sections": spec.sections,
        "coverage": coverage,
        "qc_score": qc_q,
        "confidence": {
            "level": spec.confidence_level,
            "reason": reasons[spec.confidence_level],
            "rule_ids": ["C1"],
        },
        "is_mock": True,
    }


def _build_sections(detail: WellDetail) -> list[dict[str, Any]]:
    spec = detail.spec
    name = spec.sections[-1] if spec.sections else "unknown"
    return [{
        "name": name,
        "size_in": _SIZE_IN_MAP.get(name, 0.0),
        "md_top": detail.md_start,
        "md_base": detail.md_end,
        "t_start": detail.t0_ms,
        "t_end": detail.t0_ms + spec.dense_days * 86_400 * 1000,
        "casing_shoe_md": None,
        "casing_od_in": None,
    }]


def _build_depthtime(detail: WellDetail, stride_s: int = 60) -> dict[str, Any]:
    hole = detail.channels["HOLEDEPTH"].values
    bit = detail.channels["BITDEPTH"].values
    idx = range(0, len(hole), stride_s)
    t = [detail.t0_ms + i * 1000 for i in idx]
    hole_md = [None if _isnan(hole[i]) else float(hole[i]) for i in idx]
    bit_md = [None if _isnan(bit[i]) else float(bit[i]) for i in idx]
    return {"t": t, "bit_md": bit_md, "hole_md": hole_md}


def _isnan(x: float) -> bool:
    return x != x  # noqa: PLR0124 (fast NaN check without importing math/numpy here)


def _build_rigstate(detail: WellDetail) -> list[dict[str, Any]]:
    return [
        {"t0": t0, "t1": t1, "state": state, "p": p, "rule_id": "fixture"}
        for t0, t1, state, p in detail.state_intervals
    ]


def _build_ddr(detail: WellDetail) -> list[dict[str, Any]]:
    rows = []
    for i, row in enumerate(detail.ddr_rows):
        t0, t1, code, narrative, report_date, npt, md_from, md_to = row
        rows.append({
            "id": f"ddr_{detail.spec.id}_{i}",
            "t0": t0,
            "t1": t1,
            "code": code,
            "raw_code": None,
            "md_from": md_from,
            "md_to": md_to,
            "narrative": narrative,
            "report_date": report_date,
            "npt": npt,
        })
    return rows


def _export_series(detail: WellDetail, well_dir: Path) -> dict[str, Any]:
    channels: dict[str, Any] = {}
    for ch_id, series in detail.channels.items():
        channels[ch_id] = export_channel_series(
            well_dir, ch_id, series.unit, "fixtures/synth.py", detail.t0_ms, series.values
        )
    index = {"well": detail.spec.id, "channels": channels}
    _write_json(well_dir / "series" / "index.json", index)
    return index


def _build_sessions(
    well_a: WellDetail, ilt_a: dict[str, Any], kpi_a: dict[str, Any], reg: EvidenceRegistry
) -> list[dict[str, Any]]:
    """3 recorded sessions: a verified answer, one with a deliberately unverified claim, and
    one honest `insufficient_data`. Claims in the first two reuse real evidence ids/values
    already registered by compute_ilt/compute_kpis — never invented numbers."""
    section = well_a.spec.sections[-1] if well_a.spec.sections else "section"
    total_q = ilt_a["total"]
    reaming_q = next(c["hours"] for c in ilt_a["by_category"] if c["category"] == "unreported_reaming")

    sessions = []

    answer_1 = {
        "kind": "answer",
        "answer": (
            f"In the {section} section on {well_a.spec.name}, invisible lost time totals "
            f"{total_q['value']:.1f} h against the composite-best baseline, including "
            f"{reaming_q['value']:.1f} h of reaming time embedded in rows the report codes as DRILL."
        ),
        "claims": [
            {
                "text": "Total invisible lost time", "value": total_q["value"], "unit": "h",
                "evidence_id": total_q["evidence_id"], "verified": True,
            },
            {
                "text": "Unreported reaming", "value": reaming_q["value"], "unit": "h",
                "evidence_id": reaming_q["evidence_id"], "verified": True,
            },
        ],
        "ddr_quotes": [],
        "reasoning": (
            "ilt_breakdown aggregated connection/trip overruns vs. the section's composite "
            "best (P10), plus reaming/circulating time found inside DRILL-coded DDR rows."
        ),
        "assumptions": [
            "Composite best = P10 of this section's own connection durations.",
            "4-minute data gaps are excluded, not interpolated.",
        ],
        "confidence": "high",
        "confidence_reason": (
            "core-channel coverage in the dense window is full and the section has enough samples."
        ),
        "trace": [{
            "i": 0, "tool": "ilt_breakdown", "args": {"well": well_a.spec.id, "by": "category"},
            "ms": 420, "status": "ok",
            "evidence_ids": [total_q["evidence_id"], reaming_q["evidence_id"]],
        }],
    }
    sessions.append(("s1_ilt_breakdown", f"What drove the lost time in the {section} section?", answer_1))

    unverified_value = round(total_q["value"] * 1.3, 1)  # deliberately wrong — not what evidence says
    verify_note = f"evidence {total_q['evidence_id']} records {total_q['value']:.2f} h, not {unverified_value} h"
    answer_2 = {
        "kind": "answer",
        "answer": f"Invisible lost time on {well_a.spec.name} is approximately {unverified_value} h.",
        "claims": [{
            "text": "Total invisible lost time", "value": unverified_value, "unit": "h",
            "evidence_id": total_q["evidence_id"], "verified": False, "verify_note": verify_note,
        }],
        "ddr_quotes": [],
        "reasoning": "Recorded as a deliberate example of the verifier catching a wrong number.",
        "assumptions": [],
        "confidence": "medium",
        "confidence_reason": "the claim failed verification against its own cited evidence.",
        "trace": [{
            "i": 0, "tool": "ilt_breakdown", "args": {"well": well_a.spec.id}, "ms": 310,
            "status": "ok", "evidence_ids": [total_q["evidence_id"]],
        }],
        "unverified_numbers_in_text": [str(unverified_value)],
    }
    sessions.append(("s2_unverified_example", "Give me the one-line lost-time number.", answer_2))

    answer_3 = {
        "kind": "insufficient_data",
        "answer": "There isn't enough trip data on this well to report a trip-speed KPI.",
        "claims": [],
        "ddr_quotes": [],
        "reasoning": "kpi_trips returned zero trip_in/trip_out intervals for this well in the dense window.",
        "assumptions": [],
        "confidence": "low",
        "confidence_reason": "sample size is 0 for trip speed on this well.",
        "trace": [{
            "i": 0, "tool": "kpi_trips", "args": {"well": "15_9-F-5", "direction": "in"},
            "ms": 180, "status": "ok", "evidence_ids": [],
        }],
    }
    sessions.append(("s3_insufficient_data", "What's the trip-in speed for 15/9-F-5?", answer_3))

    return [{"id": sid, "question": q, "answer": a} for sid, q, a in sessions]


def _write_sessions(sessions: list[dict[str, Any]], well_id: str, out_dir: Path) -> None:
    index_entries = []
    for s in sessions:
        session_dir = out_dir / "copilot" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        events = [
            {"type": "start", "session_id": s["id"], "dt_ms": 0, "context": {"screen": "performance", "well": well_id}},
            *[{"type": "tool_call", "step": step, "dt_ms": 200} for step in s["answer"]["trace"]],
            *[{"type": "tool_result", "step": step, "dt_ms": step["ms"]} for step in s["answer"]["trace"]],
            {"type": "answer", "answer": s["answer"], "dt_ms": 400},
        ]
        with open(session_dir / f"{s['id']}.jsonl", "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev, sort_keys=True) + "\n")
        index_entries.append({
            "id": s["id"], "question": s["question"],
            "context": {"screen": "performance", "well": well_id},
            "file": f"copilot/sessions/{s['id']}.jsonl",
            "recorded_at": datetime.now(UTC).isoformat(), "model": "fixture",
        })
    _write_json(out_dir / "copilot" / "sessions" / "index.json", {"sessions": index_entries})


def generate(out_dir: Path = OUT_DIR) -> None:
    reg = EvidenceRegistry(git_commit=_git_commit())
    well_summaries = []
    reconciliations: list[dict[str, Any]] = []
    well_a_detail: WellDetail | None = None
    well_a_ilt: dict[str, Any] | None = None
    well_a_kpi: dict[str, Any] | None = None

    for i, spec in enumerate(WELLS):
        well_summaries.append(well_summary(spec, reg))
        if not spec.detailed:
            continue

        detail = synthesize_well(spec, seed=100 + i)
        well_dir = out_dir / "wells" / spec.id

        _write_json(well_dir / "sections.json", _build_sections(detail))
        _write_json(well_dir / "depthtime.json", _build_depthtime(detail))
        _write_json(well_dir / "rigstate.json", _build_rigstate(detail))
        _write_json(well_dir / "ddr.json", _build_ddr(detail))

        mismatches = compute_mismatches(detail, reg)
        _write_json(well_dir / "mismatches.json", mismatches)

        kpis = compute_kpis(detail, reg)
        _write_json(well_dir / "kpis.json", kpis)

        ilt = compute_ilt(detail, reg, kpis)
        _write_json(well_dir / "ilt.json", ilt)

        recon = compute_reconciliation(detail, reg)
        _write_json(out_dir / "reconciliation" / f"{spec.id}.json", recon)
        reconciliations.append(recon)

        _export_series(detail, well_dir)

        if spec.id == "15_9-F-11_A":
            well_a_detail, well_a_ilt, well_a_kpi = detail, ilt, kpis

    _write_json(out_dir / "wells.json", {"wells": well_summaries, "generated_at": datetime.now(UTC).isoformat()})
    _write_json(out_dir / "issues.json", [])

    all_agreement = [a for r in reconciliations for a in r.get("per_well", [])]
    _write_json(out_dir / "reconciliation" / "all.json", {
        "scope": "all", "rows": [], "cols": [], "cells": [], "agreement": [],
        "per_well": all_agreement, "tolerance": {"boundary_slack_min": 5, "min_duration_min": 2},
    })

    assert well_a_detail is not None and well_a_ilt is not None and well_a_kpi is not None
    sessions = _build_sessions(well_a_detail, well_a_ilt, well_a_kpi, reg)
    _write_sessions(sessions, well_a_detail.spec.id, out_dir)

    qc_entries = []
    rigstate_agreement = []
    for spec in WELLS:
        if spec.detailed:
            gap_h = 4.0 / 60.0 * spec.dense_days  # one 4-min gap/day, in hours
        else:
            gap_h = 0.0
        qc_entries.append({
            "well": spec.id,
            "gap_hours": reg.quantity("qc.gaps", {"well": spec.id}, gap_h, "h", [], 2),
            "spikes_removed": 0,
            "unit_fixes": 0,
            "sentinels_removed": 0,
        })
        rigstate_agreement.append({"well": spec.id, "agreement": None})  # no gold labels yet (Sergei)

    _write_json(out_dir / "eval.json", {
        "qc": qc_entries,
        "rigstate_agreement": rigstate_agreement,
        "gold_set": {"n_questions": 0, "version": "0.0", "author": "pending", "status": "pending"},
        "ablation": [
            {"config": cfg, "metrics": {
                "answer_correctness": None, "numbers_verified_pct": None,
                "unsupported_numbers": None, "correct_insufficient_pct": None, "median_latency_s": None,
            }}
            for cfg in ("no_tools", "simple_rag", "full", "full_minus_physics")
        ],
    })

    reg.write_shards(out_dir)

    data_files = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            data = p.read_bytes()
            data_files.append({
                "path": str(p.relative_to(out_dir)),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            })
    _write_json(out_dir / "repro.json", {
        "git_commit": reg.git_commit,
        "data_files": data_files,
        "command": "make fixtures",
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline_version": "0.0.0",
    })


if __name__ == "__main__":
    generate()
