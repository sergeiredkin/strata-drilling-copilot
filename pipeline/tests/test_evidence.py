import json

from strata_pipeline.evidence import EvidenceRegistry


def test_quantity_round_trips_and_is_deterministic():
    sources = [{"file": "a", "sha256": "x"}]
    reg = EvidenceRegistry(git_commit="abc123")
    q1 = reg.quantity("kpi.connection_times", {"well": "X"}, 6.8, "min", sources)
    reg2 = EvidenceRegistry(git_commit="abc123")
    q2 = reg2.quantity("kpi.connection_times", {"well": "X"}, 6.8, "min", sources)
    assert q1["evidence_id"] == q2["evidence_id"]
    assert reg.get(q1["evidence_id"])["value"] == 6.8


def test_write_shards(tmp_path):
    reg = EvidenceRegistry()
    q = reg.quantity("qc.score", {}, 0.91, "1", [{"file": "b", "sha256": "y"}])
    reg.write_shards(tmp_path)

    shards_index = json.loads((tmp_path / "evidence" / "shards.json").read_text())
    shard = shards_index[q["evidence_id"]]
    records = json.loads((tmp_path / "evidence" / f"{shard}.json").read_text())
    assert records[q["evidence_id"]]["value"] == 0.91
