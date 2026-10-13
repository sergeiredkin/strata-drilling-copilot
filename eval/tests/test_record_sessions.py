from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from strata_eval.record_sessions import DemoQuestion, main_async
from strata_pipeline.contracts import CopilotContext


class FakeToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class FakeResponse:
    def __init__(self, content: list[Any]) -> None:
        self.content = content


class OneShotAnswerClient:
    """Immediately calls submit_answer with a fixed, evidence-free answer — enough to exercise
    the record_sessions driver end to end without needing real tool data or credentials."""

    async def create_message(self, *, model, system, tools, messages):  # type: ignore[no-untyped-def]
        answer = {
            "kind": "insufficient_data",
            "answer": "fake answer for a test",
            "claims": [],
            "ddr_quotes": [],
            "reasoning": "fake",
            "assumptions": [],
            "confidence": "low",
            "confidence_reason": "test fixture",
            "trace": [],
        }
        return FakeResponse([FakeToolUseBlock(id="call_1", name="submit_answer", input=answer)])


def test_main_async_without_api_key_or_client_exits_nonzero_without_crashing(tmp_path: Path) -> None:
    exit_code = asyncio.run(main_async(tmp_path, model=None, client=None, questions=[]))
    assert exit_code == 1


def test_main_async_records_a_session_with_a_fake_client(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    questions = [
        DemoQuestion(
            session_id="s4_lost_time_12_1_4",
            question="What drove the lost time?",
            context=CopilotContext(screen="performance", well="15_9-F-11_A"),
        )
    ]
    exit_code = asyncio.run(
        main_async(tmp_path, model="fake-model", client=OneShotAnswerClient(), questions=questions)
    )
    assert exit_code == 0

    jsonl_path = tmp_path / "copilot" / "sessions" / "s4_lost_time_12_1_4.jsonl"
    assert jsonl_path.is_file()
    lines = [json.loads(line) for line in jsonl_path.read_text().splitlines()]
    assert lines[0]["type"] == "start"
    assert lines[-1]["type"] == "answer"

    index = json.loads((tmp_path / "copilot" / "sessions" / "index.json").read_text())
    assert any(s["id"] == "s4_lost_time_12_1_4" for s in index["sessions"])
