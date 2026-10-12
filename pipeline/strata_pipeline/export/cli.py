"""CLI entry points behind the Makefile's `pipeline`/`export`/`reproduce` targets (T3.7)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.export.generate_real import OUT_DIR, _git_commit, generate_real
from strata_pipeline.export.real_wells import DDR_DIR, REAL_WELLS, WITSML_ROOT, RealWellSpec, raw_data_available
from strata_pipeline.export.run_well import run_well


def _resolve_well(well_id: str) -> RealWellSpec:
    spec = next((w for w in REAL_WELLS if w.id == well_id), None)
    if spec is None:
        known = ", ".join(w.id for w in REAL_WELLS)
        print(f"Unknown well id {well_id!r}. Known real wells: {known}", file=sys.stderr)
        sys.exit(1)
    return spec


def _require_raw_data() -> None:
    if not raw_data_available():
        archive_root = WITSML_ROOT.parent.parent
        print(f"Raw Volve archive not found under {archive_root} — see docs/LICENSES.md §3.", file=sys.stderr)
        sys.exit(1)


def pipeline_main() -> None:
    """`make pipeline WELL=<id>`: ingest -> qc -> rigstate -> kpis -> export, one well."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--well", required=True)
    args = parser.parse_args()

    _require_raw_data()

    spec = _resolve_well(args.well)
    reg = EvidenceRegistry(git_commit=_git_commit())
    summary = run_well(
        spec.id, WITSML_ROOT, spec.wellbore_name, DDR_DIR, spec.ddr_file_prefix, OUT_DIR, reg,
        spec.travelling_block_weight,
    )
    print(
        json.dumps(
            {
                "well": summary["well"],
                "qc_score": summary["qc_score"],
                "n_rigstate_intervals": summary["n_rigstate_intervals"],
                "n_ddr_rows": summary["n_ddr_rows"],
                "well_duration_hours": summary["well_duration_hours"],
            },
            indent=2,
        )
    )


def export_main() -> None:
    """`make export`: full real-well export into apps/web/public/data (run after `make fixtures`
    so mock wells not in REAL_WELLS keep their fixture entries)."""
    _require_raw_data()
    generate_real()
    print(f"Wrote real export for {len(REAL_WELLS)} wells to {OUT_DIR}")


def reproduce_main() -> None:
    """`make reproduce WELL=<id>`: runs the well's pipeline into two fresh temp directories and
    confirms every output file is byte-identical, printing a sha256 manifest either way."""
    _require_raw_data()

    parser = argparse.ArgumentParser()
    parser.add_argument("--well", required=True)
    args = parser.parse_args()
    spec = _resolve_well(args.well)

    manifests = []
    with tempfile.TemporaryDirectory() as tmp:
        for run_idx in (0, 1):
            out_dir = Path(tmp) / f"run{run_idx}"
            reg = EvidenceRegistry(git_commit=_git_commit())
            run_well(
                spec.id, WITSML_ROOT, spec.wellbore_name, DDR_DIR, spec.ddr_file_prefix, out_dir, reg,
                spec.travelling_block_weight,
            )
            manifest = {
                str(p.relative_to(out_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out_dir.rglob("*"))
                if p.is_file()
            }
            manifests.append(manifest)

        if manifests[0] != manifests[1]:
            mismatched = [path for path in manifests[0] if manifests[0].get(path) != manifests[1].get(path)]
            print(f"NOT reproducible — {len(mismatched)} file(s) differ: {mismatched}", file=sys.stderr)
            sys.exit(1)

    print(json.dumps({"well": spec.id, "reproducible": True, "files": manifests[0]}, indent=2, sort_keys=True))
