from __future__ import annotations

import json
from pathlib import Path

from strata_api.copilot.recorder import events_to_jsonl, record_session
from strata_pipeline.contracts import CopilotContext


def test_events_to_jsonl_converts_absolute_dt_ms_to_per_line_deltas() -> None:
    events = [
        {"type": "start", "dt_ms": 0.5},
        {"type": "tool_call", "dt_ms": 10.0},
        {"type": "answer", "dt_ms": 25.0},
    ]
    lines = [json.loads(line) for line in events_to_jsonl(events).splitlines()]
    assert [line["dt_ms"] for line in lines] == [0.5, 9.5, 15.0]
    assert [line["type"] for line in lines] == ["start", "tool_call", "answer"]


def test_events_to_jsonl_empty_list_returns_empty_string() -> None:
    assert events_to_jsonl([]) == ""


def test_record_session_writes_jsonl_and_index_entry(tmp_path: Path) -> None:
    events = [{"type": "start", "dt_ms": 0.0}, {"type": "answer", "dt_ms": 5.0}]
    entry = record_session(
        tmp_path, "demo_1", "a question?", CopilotContext(screen="performance"), "fake-model", events
    )
    assert entry["id"] == "demo_1"

    jsonl_path = tmp_path / "copilot" / "sessions" / "demo_1.jsonl"
    assert jsonl_path.is_file()
    assert len(jsonl_path.read_text().splitlines()) == 2

    index = json.loads((tmp_path / "copilot" / "sessions" / "index.json").read_text())
    assert [s["id"] for s in index["sessions"]] == ["demo_1"]


def test_record_session_preserves_other_sessions_and_replaces_by_id(tmp_path: Path) -> None:
    ctx = CopilotContext(screen="performance")
    record_session(tmp_path, "a", "q_a", ctx, "fake-model", [{"type": "answer", "dt_ms": 0.0}])
    record_session(tmp_path, "b", "q_b", ctx, "fake-model", [{"type": "answer", "dt_ms": 0.0}])
    record_session(tmp_path, "a", "q_a_v2", ctx, "fake-model", [{"type": "answer", "dt_ms": 0.0}])

    index = json.loads((tmp_path / "copilot" / "sessions" / "index.json").read_text())
    by_id = {s["id"]: s for s in index["sessions"]}
    assert set(by_id) == {"a", "b"}
    assert by_id["a"]["question"] == "q_a_v2"
