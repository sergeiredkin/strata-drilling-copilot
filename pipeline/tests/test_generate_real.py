import json
from typing import Any

import pytest
from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.export import generate_real as gr
from strata_pipeline.export.real_wells import RealWellSpec

ONE_WELL = [RealWellSpec(id="15_9-F-11_A", wellbore_name="15/9-F-11 A", ddr_file_prefix="15_9_F_11_A")]


def _fake_run_well(well_id, witsml_root, wellbore_name, ddr_dir, ddr_file_prefix, out_dir, reg, *args, **kwargs):
    # Mirrors run_well's real return shape closely enough to exercise generate_real's own logic
    # (merging/writing), without touching the real archive.
    (out_dir / "wells" / well_id).mkdir(parents=True, exist_ok=True)
    gap_q = reg.quantity("qc.gaps", {"well": well_id}, 1.5, "h", [], 2)
    qc = {
        "well": well_id, "gap_hours": gap_q, "spikes_removed": 2, "unit_fixes": 0, "sentinels_removed": 1,
    }
    coverage = {
        "time_logs": "full", "daily_reports": "full", "depth_logs": "none",
        "tops": "none", "survey": "none", "mud": "none",
    }
    agreement = {"value": 90.0, "unit": "%", "evidence_id": "ev_x"}
    return {
        "well": well_id,
        "qc": qc,
        "qc_score": 0.8,
        "coverage": coverage,
        "well_duration_hours": 100.0,
        "reconciliation": {"per_well": [{"well": well_id, "agreement": agreement}]},
        "n_rigstate_intervals": 10,
        "n_ddr_rows": 5,
        "issues": [
            {
                "id": f"issue_{well_id}_0",
                "well": well_id,
                "type": "tight_hole",
                "t0": 1000,
                "t1": 2000,
                "md": 2600.0,
                "formation": None,
                "section": None,
                "duration": None,
                "mud": None,
                "ddr_activity_ids": [f"ddr_{well_id}_0"],
                "excerpt": "Observed overpull.",
                "report_date": "2013-05-20",
                "extraction": "rule",
            }
        ],
    }


@pytest.fixture(autouse=True)
def _patch_run_well(monkeypatch):
    monkeypatch.setattr(gr, "run_well", _fake_run_well)
    monkeypatch.setattr(gr, "raw_data_available", lambda: True)


def test_generate_real_raises_if_raw_data_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "raw_data_available", lambda: False)
    with pytest.raises(FileNotFoundError):
        gr.generate_real(tmp_path, ONE_WELL)


def test_generate_real_writes_wells_json_with_real_well_entry(tmp_path):
    gr.generate_real(tmp_path, ONE_WELL)
    wells = json.loads((tmp_path / "wells.json").read_text())
    entry = next(w for w in wells["wells"] if w["id"] == "15_9-F-11_A")
    assert entry["is_mock"] is False
    assert entry["name"] == "15/9-F-11 A"
    assert entry["qc_score"]["value"] == 0.8


def test_generate_real_preserves_existing_mock_wells_not_in_real_roster(tmp_path):
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "wells.json").write_text(
        json.dumps({"wells": [{"id": "58-32", "is_mock": True, "name": "58-32"}], "generated_at": "x"})
    )
    gr.generate_real(tmp_path, ONE_WELL)
    wells = json.loads((tmp_path / "wells.json").read_text())
    ids = {w["id"] for w in wells["wells"]}
    assert ids == {"58-32", "15_9-F-11_A"}


def test_generate_real_overwrites_same_well_id_not_duplicates(tmp_path):
    (tmp_path / "wells.json").write_text(
        json.dumps({"wells": [{"id": "15_9-F-11_A", "is_mock": True, "name": "stale"}], "generated_at": "x"})
    )
    gr.generate_real(tmp_path, ONE_WELL)
    wells = json.loads((tmp_path / "wells.json").read_text())
    matches = [w for w in wells["wells"] if w["id"] == "15_9-F-11_A"]
    assert len(matches) == 1
    assert matches[0]["is_mock"] is False


def test_generate_real_merges_eval_json_qc_entries(tmp_path):
    existing_qc_entry = {
        "well": "58-32",
        "gap_hours": {"value": 0, "unit": "h", "evidence_id": "e"},
        "spikes_removed": 0,
        "unit_fixes": 0,
        "sentinels_removed": 0,
    }
    (tmp_path / "eval.json").write_text(
        json.dumps(
            {
                "qc": [existing_qc_entry],
                "rigstate_agreement": [{"well": "58-32", "agreement": None}],
                "gold_set": {"n_questions": 0, "version": "0.0", "author": "pending", "status": "pending"},
                "ablation": [],
            }
        )
    )
    gr.generate_real(tmp_path, ONE_WELL)
    ev = json.loads((tmp_path / "eval.json").read_text())
    qc_wells = {e["well"] for e in ev["qc"]}
    assert qc_wells == {"58-32", "15_9-F-11_A"}


def test_generate_real_writes_evidence_shards_and_repro_manifest(tmp_path):
    gr.generate_real(tmp_path, ONE_WELL)
    assert (tmp_path / "evidence" / "shards.json").exists()
    repro = json.loads((tmp_path / "repro.json").read_text())
    assert repro["command"] == "make export"
    assert any(f["path"] == "wells.json" for f in repro["data_files"])


def test_generate_real_writes_issues_json_with_extracted_events(tmp_path):
    gr.generate_real(tmp_path, ONE_WELL)
    issues = json.loads((tmp_path / "issues.json").read_text())
    assert [i["id"] for i in issues] == ["issue_15_9-F-11_A_0"]


def test_generate_real_merges_issues_json_preserving_other_wells(tmp_path):
    (tmp_path / "issues.json").write_text(
        json.dumps([{"id": "issue_58-32_0", "well": "58-32", "type": "losses"}])
    )
    gr.generate_real(tmp_path, ONE_WELL)
    issues = json.loads((tmp_path / "issues.json").read_text())
    ids = {i["id"] for i in issues}
    assert ids == {"issue_58-32_0", "issue_15_9-F-11_A_0"}


def test_merge_write_shards_preserves_prior_registry_evidence(tmp_path):
    reg1 = EvidenceRegistry(git_commit="a")
    reg1.quantity("qc.gaps", {"well": "58-32"}, 1.0, "h", [], 2)
    gr._merge_write_shards(reg1, tmp_path)

    reg2 = EvidenceRegistry(git_commit="b")
    reg2.quantity("qc.gaps", {"well": "15_9-F-11_A"}, 2.0, "h", [], 2)
    gr._merge_write_shards(reg2, tmp_path)

    shard_of: dict[str, Any] = json.loads((tmp_path / "evidence" / "shards.json").read_text())
    assert len(shard_of) == 2
    for eid, shard in shard_of.items():
        shard_contents = json.loads((tmp_path / "evidence" / f"{shard}.json").read_text())
        assert eid in shard_contents
