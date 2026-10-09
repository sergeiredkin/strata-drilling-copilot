"""T1.2 acceptance checks: every fixture JSON validates against the schema, every evidence_id
referenced exists, and the ILT sums (total == Σ category == Σ section == Σ day) hold.

Generates into a temp dir, not the real apps/web/public/data — these tests must never clobber
the committed static export (e.g. bump its generated_at) just by running `make test`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from strata_pipeline import contracts as c
from strata_pipeline.fixtures.generate import generate
from strata_pipeline.fixtures.wells import WELLS


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures-export")
    generate(out_dir=path)
    return path


def _load(path: Path) -> object:
    return json.loads(path.read_text())


def test_wells_json_validates(out_dir: Path) -> None:
    c.WellList.model_validate(_load(out_dir / "wells.json"))


def test_eval_json_validates(out_dir: Path) -> None:
    c.EvalReport.model_validate(_load(out_dir / "eval.json"))


def test_repro_json_validates(out_dir: Path) -> None:
    c.ReproManifest.model_validate(_load(out_dir / "repro.json"))


def test_issues_json_validates(out_dir: Path) -> None:
    assert _load(out_dir / "issues.json") == []


@pytest.mark.parametrize("well_id", [w.id for w in WELLS if w.detailed])
def test_detailed_well_files_validate(out_dir: Path, well_id: str) -> None:
    well_dir = out_dir / "wells" / well_id
    for name, model in [
        ("sections.json", None),
        ("depthtime.json", c.DepthTimeBlock),
        ("rigstate.json", None),
        ("ddr.json", None),
        ("mismatches.json", None),
        ("kpis.json", c.KpiReport),
        ("ilt.json", c.IltReport),
    ]:
        payload = _load(well_dir / name)
        if model is not None:
            model.model_validate(payload)
        elif isinstance(payload, list):
            for item in payload:
                if name == "sections.json":
                    c.Section.model_validate(item)
                elif name == "rigstate.json":
                    c.RigStateInterval.model_validate(item)
                elif name == "ddr.json":
                    c.DdrActivity.model_validate(item)
                elif name == "mismatches.json":
                    c.Mismatch.model_validate(item)

    c.SeriesIndex.model_validate(_load(well_dir / "series" / "index.json"))


def test_reconciliation_files_validate(out_dir: Path) -> None:
    for well in WELLS:
        if not well.detailed:
            continue
        c.Reconciliation.model_validate(_load(out_dir / "reconciliation" / f"{well.id}.json"))
    c.Reconciliation.model_validate(_load(out_dir / "reconciliation" / "all.json"))


def test_copilot_sessions_validate(out_dir: Path) -> None:
    index = _load(out_dir / "copilot" / "sessions" / "index.json")
    c.SessionIndex.model_validate(index)
    for session in index["sessions"]:  # type: ignore[index]
        lines = (out_dir / session["file"]).read_text().splitlines()
        for line in lines:
            c.CopilotEvent.model_validate(json.loads(line))


def _all_evidence_ids_in_json(obj: object) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "evidence_id" and isinstance(v, str):
                found.add(v)
            found |= _all_evidence_ids_in_json(v)
    elif isinstance(obj, list):
        for item in obj:
            found |= _all_evidence_ids_in_json(item)
    return found


def test_every_referenced_evidence_id_exists(out_dir: Path) -> None:
    shard_index = _load(out_dir / "evidence" / "shards.json")
    assert isinstance(shard_index, dict)

    referenced: set[str] = set()
    for path in out_dir.rglob("*.json"):
        if "evidence" in path.parts:
            continue
        referenced |= _all_evidence_ids_in_json(_load(path))

    missing = referenced - set(shard_index.keys())
    assert not missing, f"referenced evidence ids with no record: {missing}"


def test_ilt_sums_hold_for_every_detailed_well(out_dir: Path) -> None:
    for well in WELLS:
        if not well.detailed:
            continue
        ilt = _load(out_dir / "wells" / well.id / "ilt.json")
        total = ilt["total"]["value"]  # type: ignore[index]
        cat_sum = sum(c_["hours"]["value"] for c_ in ilt["by_category"])  # type: ignore[index]
        sec_sum = sum(s["total"]["value"] for s in ilt["by_section"])  # type: ignore[index]
        day_sum = sum(d["hours"]["value"] for d in ilt["by_day"])  # type: ignore[index]
        assert total == pytest.approx(cat_sum, abs=1e-6)
        assert total == pytest.approx(sec_sum, abs=1e-6)
        assert total == pytest.approx(day_sum, abs=1e-6)


def test_mock_badge_flag_set_on_every_well(out_dir: Path) -> None:
    wells = _load(out_dir / "wells.json")["wells"]  # type: ignore[index]
    assert all(w["is_mock"] is True for w in wells)


def test_no_fabricated_vendor_or_setpoint_copy(out_dir: Path) -> None:
    forbidden = re.compile(
        r"autopilot|optimal setpoint|recommended wob|recommended rpm|guaranteed|% npt reduction|fleet-wide",
        re.IGNORECASE,
    )
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix in (".json", ".jsonl"):
            assert not forbidden.search(path.read_text()), path
