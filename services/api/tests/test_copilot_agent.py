"""Unit tests for the agent loop with a fake LLM client (no network, no API key) —
docs/02_IMPLEMENTATION_PLAN.md T8.4's acceptance criterion. Runs against the repo's own
committed fixture export, same as test_routes.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import BaseModel
from strata_api.copilot.agent import run_agent
from strata_api.settings import Settings
from strata_pipeline.contracts import CopilotContext

FIXTURE_DATA_DIR = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "data"
WELL = "15_9-F-11_A"


@pytest.fixture
def settings() -> Settings:
    return Settings(data_dir=FIXTURE_DATA_DIR, cors_origins=[])


@pytest.fixture
def well_span() -> tuple[float, float]:
    rows = json.loads((FIXTURE_DATA_DIR / "wells" / WELL / "rigstate.json").read_text())
    return min(r["t0"] for r in rows), max(r["t1"] for r in rows)


class FakeToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class FakeTextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class FakeResponse:
    def __init__(self, content: list[Any]) -> None:
        self.content = content


class ScriptedLlmClient:
    """Each entry in `turns` is called with the conversation so far and returns the next
    `FakeResponse` — lets a later turn react to an earlier tool's real result (e.g. pick up an
    evidence id minted by the previous tool call) instead of being a fully fixed script."""

    def __init__(self, turns: list[Any]) -> None:
        self._turns = turns
        self.calls = 0

    async def create_message(
        self, *, model: str, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> Any:
        turn = self._turns[self.calls]
        self.calls += 1
        return turn(messages)


def _last_tool_result(messages: list[dict[str, Any]]) -> dict[str, Any]:
    last_user = messages[-1]
    assert last_user["role"] == "user"
    tool_result = last_user["content"][0]
    return json.loads(tool_result["content"])  # type: ignore[no-any-return]


@pytest.mark.asyncio
async def test_agent_verifies_a_claim_backed_by_a_freshly_minted_evidence_id(
    settings: Settings, well_span: tuple[float, float]
) -> None:
    t0, t1 = well_span

    def turn_1(_messages: list[dict[str, Any]]) -> FakeResponse:
        return FakeResponse(
            [FakeToolUseBlock(id="call_1", name="rigstate_summary", input={"well": WELL, "t0": t0, "t1": t1})]
        )

    def turn_2(messages: list[dict[str, Any]]) -> FakeResponse:
        result = _last_tool_result(messages)
        rotary = result["by_state"]["rotary_drilling"]
        answer = {
            "kind": "answer",
            "answer": f"Rotary drilling took {rotary['value']} hours in this window.",
            "claims": [
                {
                    "text": "rotary drilling hours",
                    "value": rotary["value"],
                    "unit": rotary["unit"],
                    "evidence_id": rotary["evidence_id"],
                    "verified": False,
                }
            ],
            "ddr_quotes": [],
            "reasoning": "Summed rigstate intervals for rotary_drilling in the requested window.",
            "assumptions": [],
            "confidence": "high",
            "confidence_reason": "direct sum of classified intervals",
            "trace": [],
        }
        return FakeResponse([FakeToolUseBlock(id="call_2", name="submit_answer", input=answer)])

    client = ScriptedLlmClient([turn_1, turn_2])
    events = [
        e
        async for e in run_agent(
            question="How many hours of rotary drilling happened?",
            context=CopilotContext(screen="workspace", well=WELL),
            settings=settings,
            session_id="test-session",
            client=client,
        )
    ]

    types = [e["type"] for e in events]
    assert types == ["start", "tool_call", "tool_result", "answer"]

    answer_event = events[-1]
    claims = answer_event["answer"]["claims"]
    assert len(claims) == 1
    assert claims[0]["verified"] is True
    assert answer_event["answer"]["unverified_numbers_in_text"] is None
    assert len(answer_event["answer"]["trace"]) == 1
    assert answer_event["answer"]["trace"][0]["tool"] == "rigstate_summary"


@pytest.mark.asyncio
async def test_agent_flags_a_claim_with_a_fabricated_evidence_id(settings: Settings) -> None:
    def turn_1(_messages: list[dict[str, Any]]) -> FakeResponse:
        answer = {
            "kind": "answer",
            "answer": "Rotary drilling took 1000 hours.",
            "claims": [
                {
                    "text": "rotary drilling hours",
                    "value": 1000.0,
                    "unit": "h",
                    "evidence_id": "ev_0000000000",
                    "verified": False,
                }
            ],
            "ddr_quotes": [],
            "reasoning": "made up",
            "assumptions": [],
            "confidence": "high",
            "confidence_reason": "n/a",
            "trace": [],
        }
        return FakeResponse([FakeToolUseBlock(id="call_1", name="submit_answer", input=answer)])

    client = ScriptedLlmClient([turn_1])
    events = [
        e
        async for e in run_agent(
            question="How many hours of rotary drilling happened?",
            context=CopilotContext(screen="workspace", well=WELL),
            settings=settings,
            session_id="test-session",
            client=client,
        )
    ]

    answer_event = events[-1]
    assert answer_event["type"] == "answer"
    assert answer_event["answer"]["claims"][0]["verified"] is False
    assert "unknown evidence id" in answer_event["answer"]["claims"][0]["verify_note"]


@pytest.mark.asyncio
async def test_agent_errors_gracefully_when_tool_call_budget_is_exhausted(settings: Settings) -> None:
    def spam_tool_calls(_messages: list[dict[str, Any]]) -> FakeResponse:
        return FakeResponse(
            [FakeToolUseBlock(id=f"call_{i}", name="list_wells", input={}) for i in range(13)]
        )

    client = ScriptedLlmClient([spam_tool_calls])
    events = [
        e
        async for e in run_agent(
            question="anything",
            context=CopilotContext(screen="workspace"),
            settings=settings,
            session_id="test-session",
            client=client,
        )
    ]

    assert events[-1]["type"] == "error"
    assert "budget" in events[-1]["message"]


@pytest.mark.asyncio
async def test_agent_reports_a_tool_error_without_crashing(settings: Settings) -> None:
    def turn_1(_messages: list[dict[str, Any]]) -> FakeResponse:
        return FakeResponse(
            [FakeToolUseBlock(id="call_1", name="well_summary", input={"well": "not-a-real-well"})]
        )

    def turn_2(messages: list[dict[str, Any]]) -> FakeResponse:
        last_user = messages[-1]
        tool_result = last_user["content"][0]
        assert tool_result.get("is_error") is True
        answer = {
            "kind": "insufficient_data",
            "answer": "That well id doesn't exist in this export.",
            "claims": [],
            "ddr_quotes": [],
            "reasoning": "well_summary returned an error for that id.",
            "assumptions": [],
            "confidence": "low",
            "confidence_reason": "tool error",
            "trace": [],
        }
        return FakeResponse([FakeToolUseBlock(id="call_2", name="submit_answer", input=answer)])

    client = ScriptedLlmClient([turn_1, turn_2])
    events = [
        e
        async for e in run_agent(
            question="tell me about well XYZ",
            context=CopilotContext(screen="workspace"),
            settings=settings,
            session_id="test-session",
            client=client,
        )
    ]

    assert events[-1]["type"] == "answer"
    assert events[-1]["answer"]["kind"] == "insufficient_data"
    tool_result_event = next(e for e in events if e["type"] == "tool_result")
    assert tool_result_event["step"]["status"] == "error"
