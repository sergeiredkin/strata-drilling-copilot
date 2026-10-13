"""3-question smoke test with a fake LLM client — docs/02_IMPLEMENTATION_PLAN.md T9.2's
acceptance criterion ("runs end-to-end on a 3-question smoke set with fake LLM"). The real gold
set (eval/gold/questions.yaml) stays status=pending until Sergei has >= 25 real questions; this
proves the ablation+scoring machinery itself works, independent of that.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from strata_api.settings import Settings
from strata_eval.run_ablation import ABLATION_CONFIGS, GoldQuestion, GoldSetMeta, run_all
from strata_eval.score import update_eval_json
from strata_pipeline.contracts import CopilotContext, EvalReport

FIXTURE_DATA_DIR = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "data"

SMOKE_QUESTIONS = [
    GoldQuestion(
        id="smoke-1",
        question="How much flat time was there?",
        context=CopilotContext(screen="performance", well="15_9-F-11_A"),
        expected_kind="answer",
        expected_numbers=[],
    ),
    GoldQuestion(
        id="smoke-2",
        question="What's the trip-in speed for a well that isn't exported?",
        context=CopilotContext(screen="performance"),
        expected_kind="insufficient_data",
        expected_numbers=[],
    ),
    GoldQuestion(
        id="smoke-3",
        question="What drove the lost time in the 8½ section?",
        context=CopilotContext(screen="performance", well="15_9-F-11_A", section="8½"),
        expected_kind="answer",
        expected_numbers=[],
    ),
]


class FakeToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class FakeResponse:
    def __init__(self, content: list[Any]) -> None:
        self.content = content


def _already_has_tool_result(messages: list[dict[str, Any]]) -> bool:
    last = messages[-1]
    content = last.get("content")
    return (
        last.get("role") == "user"
        and isinstance(content, list)
        and bool(content)
        and isinstance(content[0], dict)
        and content[0].get("type") == "tool_result"
    )


class SmartFakeClient:
    """Stateless per call (decides purely from the conversation so far), so one instance can be
    reused across every (question, config) pair `run_all` drives it through: if a non-
    `submit_answer` tool is available and hasn't been called yet, call `list_wells` (the one tool
    with no required arguments, available in every config that allows any tools at all);
    otherwise submit a scripted answer matching the question's expected kind."""

    async def create_message(
        self, *, model: str, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> FakeResponse:
        tool_names = [t["name"] for t in tools if t["name"] != "submit_answer"]
        if tool_names and not _already_has_tool_result(messages):
            return FakeResponse([FakeToolUseBlock(id="call_1", name="list_wells", input={})])

        question_text = messages[0]["content"] if isinstance(messages[0]["content"], str) else ""
        kind = "insufficient_data" if "isn't exported" in question_text else "answer"
        answer = {
            "kind": kind,
            "answer": "scripted smoke-test answer" if kind == "answer" else "insufficient data for this well",
            "claims": [],
            "ddr_quotes": [],
            "reasoning": "fake",
            "assumptions": [],
            "confidence": "low",
            "confidence_reason": "smoke test fixture",
            "trace": [],
        }
        return FakeResponse([FakeToolUseBlock(id="call_2", name="submit_answer", input=answer)])


def test_run_all_and_score_produce_a_schema_valid_eval_report(tmp_path: Path) -> None:
    settings = Settings(data_dir=FIXTURE_DATA_DIR, cors_origins=[])
    client = SmartFakeClient()

    results = asyncio.run(run_all(SMOKE_QUESTIONS, settings, client=client, model="fake-model"))
    assert len(results) == len(SMOKE_QUESTIONS) * len(ABLATION_CONFIGS)

    gold_meta = GoldSetMeta(status="pending", version="0.0", author="test", n_questions=len(SMOKE_QUESTIONS))
    eval_json_path = tmp_path / "eval.json"
    eval_json_path.write_text(json.dumps({"qc": [], "rigstate_agreement": []}), encoding="utf-8")

    updated = update_eval_json(eval_json_path, gold_meta, results)

    report = EvalReport.model_validate(updated)
    assert report.gold_set.n_questions == 3
    assert {item.config for item in report.ablation} == set(ABLATION_CONFIGS)
    for item in report.ablation:
        assert item.metrics.answer_correctness is not None
        assert item.metrics.median_latency_s is not None
