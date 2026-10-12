from __future__ import annotations

import struct

from fastapi.testclient import TestClient

WELL = "15_9-F-11_A"


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_list_wells(client: TestClient) -> None:
    res = client.get("/wells")
    assert res.status_code == 200
    body = res.json()
    assert any(w["id"] == WELL for w in body["wells"])


def test_well_sections(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/sections")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_well_sections_unknown_well_404s(client: TestClient) -> None:
    res = client.get("/wells/not-a-real-well/sections")
    assert res.status_code == 404


def test_well_depthtime(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/depthtime")
    assert res.status_code == 200
    assert "t" in res.json()


def test_well_series_index(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/series")
    assert res.status_code == 200
    assert "BITDEPTH" in res.json()["channels"]


def test_well_channel_binary_block(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/channels", params={"ch": "BITDEPTH", "level": 0})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/octet-stream"
    magic, n, t0, bucket_s, _reserved = struct.unpack_from("<4sIdfI", res.content, 0)
    assert magic == b"STRS"
    assert n > 0
    assert bucket_s == 1.0
    # header + n mins (f32) + n maxs (f32)
    assert len(res.content) == 24 + n * 4 * 2


def test_well_channel_unknown_channel_404s(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/channels", params={"ch": "NOT_A_CHANNEL", "level": 0})
    assert res.status_code == 404


def test_well_channel_unknown_level_404s(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/channels", params={"ch": "BITDEPTH", "level": 99})
    assert res.status_code == 404


def test_well_rigstate(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/rigstate")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_well_rigstate_with_window_filters(client: TestClient) -> None:
    full = client.get(f"/wells/{WELL}/rigstate").json()
    assert full
    t0, t1 = full[0]["t0"], full[0]["t1"]
    windowed = client.get(f"/wells/{WELL}/rigstate", params={"start": t0, "end": t1}).json()
    assert len(windowed) <= len(full)
    assert all(r["t1"] > t0 and r["t0"] < t1 for r in windowed)


def test_well_ddr(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/ddr")
    assert res.status_code == 200


def test_well_mismatches(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/mismatches")
    assert res.status_code == 200


def test_well_kpis(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/kpis")
    assert res.status_code == 200
    assert res.json()["well"] == WELL


def test_well_ilt(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/ilt")
    assert res.status_code == 200
    assert res.json()["well"] == WELL


def test_reconciliation_all(client: TestClient) -> None:
    res = client.get("/reconciliation")
    assert res.status_code == 200


def test_reconciliation_by_well(client: TestClient) -> None:
    res = client.get("/reconciliation", params={"well": WELL})
    assert res.status_code == 200
    assert res.json()["scope"] == WELL


def test_evidence_lookup(client: TestClient) -> None:
    kpis = client.get(f"/wells/{WELL}/kpis").json()
    evidence_id = kpis["cards"][0]["value"]["evidence_id"]
    res = client.get(f"/evidence/{evidence_id}")
    assert res.status_code == 200
    assert res.json()["id"] == evidence_id


def test_evidence_unknown_id_404s(client: TestClient) -> None:
    res = client.get("/evidence/ev_0000000000")
    assert res.status_code == 404


def test_eval_report(client: TestClient) -> None:
    res = client.get("/eval")
    assert res.status_code == 200


def test_repro_manifest(client: TestClient) -> None:
    res = client.get("/meta/repro")
    assert res.status_code == 200


def test_copilot_sessions(client: TestClient) -> None:
    res = client.get("/copilot/sessions")
    assert res.status_code == 200
    assert "sessions" in res.json()


def test_copilot_ask_streams_live_mode_required_answer(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/copilot/ask",
        json={"question": "test?", "context": {"screen": "workspace"}},
    ) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())
    assert "live_mode_required" in body


def test_issues_empty_fixture_list(client: TestClient) -> None:
    res = client.get("/issues")
    assert res.status_code == 200
    assert res.json() == []


def test_formations_404s_when_not_yet_produced(client: TestClient) -> None:
    res = client.get(f"/wells/{WELL}/formations")
    assert res.status_code == 404
