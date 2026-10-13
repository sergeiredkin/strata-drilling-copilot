"""Recorder — docs/03_ARCHITECTURE.md §4 ("in live mode every session can be saved as JSONL
into copilot/sessions/") and docs/04_DATA_CONTRACTS.md §5 (one `CopilotEvent` per line, each
with `dt_ms` *since the previous event*, last line `answer` or `error`) + §3 (the
`copilot/sessions/index.json` + `copilot/sessions/{id}.jsonl` layout). `run_agent` itself emits
each event's `dt_ms` as elapsed time since the *session started* (a monotonic clock, convenient
for the live SSE stream); this module converts that into the per-line delta the static-mode
replay format actually needs, and writes both the session file and its index entry."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from strata_pipeline.contracts import CopilotContext


def events_to_jsonl(events: list[dict[str, Any]]) -> str:
    """One compact JSON object per line, `dt_ms` rewritten from "since session start" to "since
    the previous line" (0 for the first line)."""
    lines = []
    previous_dt_ms = 0.0
    for event in events:
        absolute_dt_ms = event.get("dt_ms", previous_dt_ms)
        delta_ms = max(0.0, absolute_dt_ms - previous_dt_ms)
        previous_dt_ms = absolute_dt_ms
        lines.append(json.dumps({**event, "dt_ms": delta_ms}))
    return "\n".join(lines) + ("\n" if lines else "")


def record_session(
    out_dir: Path,
    session_id: str,
    question: str,
    context: CopilotContext,
    model: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Writes `{out_dir}/copilot/sessions/{session_id}.jsonl` and merges its entry into
    `{out_dir}/copilot/sessions/index.json` (added or replaced by id, every other entry kept —
    so re-recording one demo question doesn't drop the others already there). Returns the
    index entry written."""
    sessions_dir = out_dir / "copilot" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = sessions_dir / f"{session_id}.jsonl"
    jsonl_path.write_text(events_to_jsonl(events), encoding="utf-8")

    entry = {
        "id": session_id,
        "file": f"copilot/sessions/{session_id}.jsonl",
        "question": question,
        "context": context.model_dump(exclude_none=True),
        "model": model,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    index_path = sessions_dir / "index.json"
    index: dict[str, Any] = {"sessions": []}
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    sessions = [s for s in index.get("sessions", []) if s["id"] != session_id]
    sessions.append(entry)
    sessions.sort(key=lambda s: s["id"])
    index_path.write_text(json.dumps({"sessions": sessions}, indent=2, sort_keys=True), encoding="utf-8")

    return entry
