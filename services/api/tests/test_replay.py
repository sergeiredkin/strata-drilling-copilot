from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from strata_api.replay import merge_replay_events
from strata_api.settings import Settings
from strata_pipeline.export.series import write_strs

WELL = "15_9-F-11_A"


def _write_fixture(tmp_path, values: list[float], t0_ms: float = 0.0, bucket_s: float = 1.0) -> Settings:
    well_dir = tmp_path / "wells" / "W1"
    chunk_rel = "series/HKLD/L0/0.bin"
    write_strs(well_dir / chunk_rel, t0_ms, bucket_s, np.array(values, dtype="f4"), np.array(values, dtype="f4"))
    index = {
        "well": "W1",
        "channels": {
            "HKLD": {
                "unit": "kN", "source": "test", "gaps": [],
                "levels": [
                    {
                        "level": 0, "bucket_s": bucket_s,
                        "chunks": [
                            {
                                "i": 0, "t0": t0_ms, "t1": t0_ms + len(values) * bucket_s * 1000,
                                "n": len(values), "file": chunk_rel,
                            }
                        ],
                    }
                ],
            }
        },
    }
    (well_dir / "series").mkdir(parents=True, exist_ok=True)
    (well_dir / "series" / "index.json").write_text(json.dumps(index))
    return Settings(data_dir=tmp_path, cors_origins=[])


def test_merge_replay_events_decodes_samples_in_time_order(tmp_path) -> None:
    settings = _write_fixture(tmp_path, [10.0, 20.0, 30.0])
    events = list(merge_replay_events(settings, "W1", 0.0))
    assert [e["type"] for e in events] == ["sample", "sample", "sample"]
    assert [e["t"] for e in events] == [0.0, 1000.0, 2000.0]
    assert events[0]["values"]["HKLD"] == 10.0


def test_merge_replay_events_interleaves_state_alerts_by_time(tmp_path) -> None:
    settings = _write_fixture(tmp_path, [10.0, 20.0, 30.0])
    (tmp_path / "wells" / "W1" / "replay_events.json").write_text(
        json.dumps([{"type": "state", "t": 500.0, "state": "rotary_drilling"}])
    )
    events = list(merge_replay_events(settings, "W1", 0.0))
    assert [e["t"] for e in events] == [0.0, 500.0, 1000.0, 2000.0]
    assert events[1]["type"] == "state"


def test_merge_replay_events_filters_before_from_t(tmp_path) -> None:
    settings = _write_fixture(tmp_path, [10.0, 20.0, 30.0])
    events = list(merge_replay_events(settings, "W1", 1500.0))
    assert [e["t"] for e in events] == [2000.0]


def test_merge_replay_events_empty_for_a_well_with_no_series(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, cors_origins=[])
    assert list(merge_replay_events(settings, "unknown-well", 0.0)) == []


def test_merge_replay_events_nan_becomes_null(tmp_path) -> None:
    settings = _write_fixture(tmp_path, [10.0, float("nan"), 30.0])
    events = list(merge_replay_events(settings, "W1", 0.0))
    assert events[1]["values"]["HKLD"] is None


def test_replay_ws_streams_real_events_for_the_real_well(client: TestClient) -> None:
    with client.websocket_connect(f"/replay/{WELL}?speed=60&from_t=0") as ws:
        events = [ws.receive_json() for _ in range(5)]
    assert len(events) == 5
    assert all(e["type"] in {"sample", "state", "alert"} for e in events)


def test_replay_ws_rejects_an_unsafe_well_id(client: TestClient) -> None:
    with pytest.raises(Exception):  # noqa: B017 - starlette raises on an immediate server close
        with client.websocket_connect("/replay/..%2f..%2fetc") as ws:
            ws.receive_json()
