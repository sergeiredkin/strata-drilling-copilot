"""`make export` for real wells — T3.7: runs `run_well` for every well in `real_wells.REAL_WELLS`
and writes the cross-well files (`wells.json`, `reconciliation/all.json`, `eval.json`,
evidence shards, `repro.json`) that `fixtures/generate.py` writes for mock wells. Does not touch
or replace the fixture-generated files for wells not in `REAL_WELLS` — real and mock wells
currently write to the same `apps/web/public/data/` tree, so running this after `make fixtures`
overwrites only the 6 real wells' entries.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from strata_pipeline.confidence import assess
from strata_pipeline.events.model_card import build_events_model_card
from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.export.real_wells import (
    DDR_DIR,
    REAL_WELLS,
    WELL_PICKS_CSV,
    WITSML_ROOT,
    RealWellSpec,
    raw_data_available,
)
from strata_pipeline.export.run_well import run_well
from strata_pipeline.fixtures.wells import COVERAGE_KINDS
from strata_pipeline.fixtures.wells import WELLS as MOCK_WELLS

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "apps" / "web" / "public" / "data"

_METADATA_BY_ID = {w.id: w for w in MOCK_WELLS}  # name/field/md_range/sections — public-record
# descriptive metadata, not a computed number; unaffected by whether the export is real or mock.


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


def _well_summary(spec: RealWellSpec, run_summary: dict[str, Any], reg: EvidenceRegistry) -> dict[str, Any]:
    meta = _METADATA_BY_ID[spec.id]
    coverage = [
        {
            "kind": kind,
            "status": run_summary["coverage"].get(kind, "none"),
            "rows": None,
            "span": None,
            "source_files": [],
        }
        for kind in COVERAGE_KINDS
    ]
    qc_q = reg.quantity("qc.score", {"well": spec.id}, run_summary["qc_score"], "1", [], 2)
    conf = assess(core_channel_coverage=run_summary["qc_score"])
    return {
        "id": spec.id,
        "name": meta.name,
        "field": meta.field,
        "years": meta.years,
        "md_range": list(meta.md_range),
        "sections": meta.sections,
        "coverage": coverage,
        "qc_score": qc_q,
        "confidence": conf,
        "is_mock": False,
    }


def _merge_write_shards(reg: EvidenceRegistry, out_dir: Path) -> None:
    """Like `EvidenceRegistry.write_shards`, but merges into whatever evidence shards already
    exist on disk (e.g. from `make fixtures`) instead of overwriting them — `reg` here only ever
    holds the evidence this run registered, not the mock wells'."""
    shard_dir = out_dir / "evidence"
    shards: dict[str, dict[str, Any]] = {}
    shard_of: dict[str, str] = {}
    shards_json = shard_dir / "shards.json"
    if shards_json.exists():
        shard_of = json.loads(shards_json.read_text())
        for shard in set(shard_of.values()):
            shard_file = shard_dir / f"{shard}.json"
            if shard_file.exists():
                shards[shard] = json.loads(shard_file.read_text())

    for eid, record in reg.all_records().items():
        shard = eid[3:5]
        shards.setdefault(shard, {})[eid] = record
        shard_of[eid] = shard

    shard_dir.mkdir(parents=True, exist_ok=True)
    for shard, records in shards.items():
        _write_json(shard_dir / f"{shard}.json", records)
    _write_json(shards_json, shard_of)


def generate_real(out_dir: Path = OUT_DIR, wells: list[RealWellSpec] = REAL_WELLS) -> None:
    if not raw_data_available():
        raise FileNotFoundError(
            f"Raw Volve archive not found at {WITSML_ROOT} / {DDR_DIR} — see docs/LICENSES.md §3 "
            "for the manual Databricks download steps (T2.1); this command does not fetch it."
        )

    reg = EvidenceRegistry(git_commit=_git_commit())
    well_summaries = []
    qc_entries = []
    per_well_agreement = []
    rigstate_agreement = []
    issues: list[dict[str, Any]] = []

    for spec in wells:
        summary = run_well(
            spec.id, WITSML_ROOT, spec.wellbore_name, DDR_DIR, spec.ddr_file_prefix, out_dir, reg,
            spec.travelling_block_weight,
            well_picks_csv=WELL_PICKS_CSV if WELL_PICKS_CSV.exists() else None,
        )
        well_summaries.append(_well_summary(spec, summary, reg))
        qc_entries.append(summary["qc"])
        per_well_agreement.extend(summary["reconciliation"]["per_well"])
        rigstate_agreement.append({"well": spec.id, "agreement": None})  # gold labels pending Sergei
        issues.extend(summary["issues"])

    existing_wells_path = out_dir / "wells.json"
    existing = json.loads(existing_wells_path.read_text()) if existing_wells_path.exists() else {"wells": []}
    real_ids = {w["id"] for w in well_summaries}
    merged_wells = [w for w in existing.get("wells", []) if w["id"] not in real_ids] + well_summaries
    _write_json(out_dir / "wells.json", {"wells": merged_wells, "generated_at": datetime.now(UTC).isoformat()})

    _write_json(
        out_dir / "reconciliation" / "all.json",
        {
            "scope": "all", "rows": [], "cols": [], "cells": [], "agreement": [],
            "per_well": per_well_agreement, "tolerance": {"boundary_slack_min": 5, "min_duration_min": 2},
        },
    )

    existing_issues_path = out_dir / "issues.json"
    existing_issues = json.loads(existing_issues_path.read_text()) if existing_issues_path.exists() else []
    real_issue_wells = {w["id"] for w in well_summaries}
    merged_issues = [i for i in existing_issues if i["well"] not in real_issue_wells] + issues
    _write_json(out_dir / "issues.json", merged_issues)
    _write_json(out_dir / "models" / "events_card.json", build_events_model_card(merged_issues))

    existing_eval_path = out_dir / "eval.json"
    existing_eval: dict[str, Any] = (
        json.loads(existing_eval_path.read_text())
        if existing_eval_path.exists()
        else {
            "qc": [],
            "rigstate_agreement": [],
            "gold_set": {"n_questions": 0, "version": "0.0", "author": "pending", "status": "pending"},
            "ablation": [],
        }
    )
    real_qc_wells = {e["well"] for e in qc_entries}
    merged_qc = [e for e in existing_eval["qc"] if e["well"] not in real_qc_wells] + qc_entries
    real_rs_wells = {e["well"] for e in rigstate_agreement}
    merged_rigstate = [
        e for e in existing_eval["rigstate_agreement"] if e["well"] not in real_rs_wells
    ] + rigstate_agreement
    _write_json(
        out_dir / "eval.json",
        {**existing_eval, "qc": merged_qc, "rigstate_agreement": merged_rigstate},
    )

    _merge_write_shards(reg, out_dir)

    data_files = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            data = p.read_bytes()
            data_files.append(
                {"path": str(p.relative_to(out_dir)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            )
    _write_json(
        out_dir / "repro.json",
        {
            "git_commit": reg.git_commit,
            "data_files": data_files,
            "command": "make export",
            "generated_at": datetime.now(UTC).isoformat(),
            "pipeline_version": "0.0.0",
        },
    )


if __name__ == "__main__":
    generate_real()
