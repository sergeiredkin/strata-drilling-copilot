"""Copilot agent loop — docs/03_ARCHITECTURE.md §4 + docs/07_DATA_AND_ALGORITHMS.md §12: the
Anthropic Messages API tool-use loop, ending when the model calls `submit_answer`, verified
before being handed back to the caller. `run_agent` is an async generator of `CopilotEvent`-
shaped dicts so `routes/copilot.py` can stream them over SSE as they happen; `client` is
injectable so tests can script tool calls with a fake instead of a real Anthropic connection
(docs/02_IMPLEMENTATION_PLAN.md T8.4's acceptance criterion).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Protocol

from strata_pipeline.contracts import CopilotAnswer, CopilotContext, TraceStep
from strata_pipeline.evidence import EvidenceRegistry

from ..settings import Settings
from .tools import TOOL_SPECS, CopilotTools, ToolError
from .verifier import verify_answer

MAX_TOOL_CALLS = 12
MAX_TURNS = MAX_TOOL_CALLS + 4  # a few turns of text-only chatter before submit_answer is tolerated
DEFAULT_MAX_TOKENS = 4096

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")

_SUBMIT_ANSWER_SPEC = {
    "name": "submit_answer",
    "description": "Deliver your final answer. This is the only way your answer reaches the user.",
    "input_schema": CopilotAnswer.model_json_schema(),
}


class LlmClient(Protocol):
    async def create_message(
        self, *, model: str, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> Any: ...


class AnthropicLlmClient:
    """Thin adapter over `anthropic.AsyncAnthropic` matching `LlmClient` — isolates the one
    place that imports the real SDK, so tests never need it or a key."""

    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic()

    async def create_message(
        self, *, model: str, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> Any:
        # Raw dicts matching the Messages API wire format, not the SDK's richly-typed
        # TypedDict params — valid at runtime, just not what mypy infers from `list[dict]`.
        return await self._client.messages.create(
            model=model,
            system=system,
            tools=tools,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
            max_tokens=DEFAULT_MAX_TOKENS,
        )


def _trace_step(
    i: int,
    tool: str,
    args: dict[str, Any],
    ms: float,
    status: str,
    result_summary: str | None,
    evidence_ids: list[str] | None,
) -> dict[str, Any]:
    return {
        "i": i, "tool": tool, "args": args, "ms": ms, "status": status,
        "result_summary": result_summary, "evidence_ids": evidence_ids,
    }


def _summarize(result: Any, limit: int = 300) -> str:
    text = json.dumps(result, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _collect_evidence_ids(result: Any) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            eid = node.get("evidence_id")
            if isinstance(eid, str):
                found.append(eid)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(result)
    return found


def _run_tool(tools: CopilotTools, name: str, args: dict[str, Any]) -> tuple[Any, str]:
    handler = getattr(tools, name, None)
    if handler is None:
        raise ToolError(f"unknown tool: {name!r}")
    return handler(**args), "ok"


async def run_agent(
    *,
    question: str,
    context: CopilotContext,
    settings: Settings,
    session_id: str,
    client: LlmClient | None = None,
    model: str | None = None,
    allowed_tools: set[str] | None = None,
    extra_context: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """`allowed_tools`, if given, restricts which non-`submit_answer` tools the model may call —
    used by eval/strata_eval/run_ablation.py's `no_tools`/`full_minus_physics` configs (`None`
    means every tool in `TOOL_SPECS`, i.e. the `full` config). `extra_context`, if given, is
    appended to the user turn verbatim — `run_ablation.py`'s `simple_rag` config uses this to
    inject BM25-retrieved text instead of letting the model call tools for it."""
    start = time.monotonic()

    def dt_ms() -> float:
        return (time.monotonic() - start) * 1000.0

    yield {"type": "start", "session_id": session_id, "dt_ms": dt_ms(), "context": context.model_dump()}

    llm = client or AnthropicLlmClient()
    model_id = model or os.environ.get("STRATA_LLM_MODEL", "claude-sonnet-5-5")
    reg = EvidenceRegistry(git_commit=os.environ.get("STRATA_GIT_COMMIT", "unknown"))
    tools = CopilotTools(settings, reg)
    specs = TOOL_SPECS if allowed_tools is None else [s for s in TOOL_SPECS if s["name"] in allowed_tools]
    all_specs = [*specs, _SUBMIT_ANSWER_SPEC]

    question_block = f"Context: {context.model_dump_json()}\n\nQuestion: {question}"
    if extra_context:
        question_block += f"\n\n{extra_context}"
    messages: list[dict[str, Any]] = [{"role": "user", "content": question_block}]

    tool_calls_used = 0
    trace: list[dict[str, Any]] = []

    for _turn in range(MAX_TURNS):
        try:
            response = await llm.create_message(
                model=model_id, system=_SYSTEM_PROMPT, tools=all_specs, messages=messages
            )
        except Exception as exc:  # noqa: BLE001 - any LLM-side failure becomes a graceful error event
            yield {"type": "error", "message": f"LLM call failed: {exc}", "dt_ms": dt_ms()}
            return

        content = list(getattr(response, "content", []))
        tool_use_blocks = [b for b in content if getattr(b, "type", None) == "tool_use"]

        submit_block = next((b for b in tool_use_blocks if b.name == "submit_answer"), None)
        if submit_block is not None:
            try:
                answer = CopilotAnswer.model_validate(submit_block.input)
            except Exception as exc:  # noqa: BLE001
                yield {"type": "error", "message": f"model's submit_answer was invalid: {exc}", "dt_ms": dt_ms()}
                return
            verified = verify_answer(answer, settings, reg)
            verified = verified.model_copy(update={"trace": [TraceStep.model_validate(s) for s in trace]})
            yield {"type": "answer", "answer": verified.model_dump(mode="json"), "dt_ms": dt_ms()}
            return

        if not tool_use_blocks:
            # Text-only turn with no submit_answer — nudge the model to finish properly rather
            # than silently discarding its prose (system prompt rule 7).
            messages.append({"role": "assistant", "content": [b.model_dump() for b in content]})
            messages.append(
                {
                    "role": "user",
                    "content": "You must call submit_answer with your final CopilotAnswer to finish.",
                }
            )
            continue

        if tool_calls_used + len(tool_use_blocks) > MAX_TOOL_CALLS:
            yield {
                "type": "error",
                "message": f"tool-call budget exhausted ({MAX_TOOL_CALLS} max) without an answer",
                "dt_ms": dt_ms(),
            }
            return

        messages.append({"role": "assistant", "content": [b.model_dump() for b in content]})
        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
            tool_calls_used += 1
            i = tool_calls_used
            call_step = _trace_step(i, block.name, block.input, 0.0, "ok", None, None)
            yield {"type": "tool_call", "step": call_step, "dt_ms": dt_ms()}

            t0 = time.monotonic()
            try:
                result, status = _run_tool(tools, block.name, block.input)
                ms = (time.monotonic() - t0) * 1000.0
                evidence_ids = _collect_evidence_ids(result)
                result_step = _trace_step(
                    i, block.name, block.input, ms, status, _summarize(result), evidence_ids or None
                )
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)}
                )
            except ToolError as exc:
                ms = (time.monotonic() - t0) * 1000.0
                result_step = _trace_step(i, block.name, block.input, ms, "error", str(exc), None)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": str(exc)}),
                        "is_error": True,
                    }
                )
            trace.append(result_step)
            yield {"type": "tool_result", "step": result_step, "dt_ms": dt_ms()}

        messages.append({"role": "user", "content": tool_results})

    yield {"type": "error", "message": "ran out of turns without a submit_answer call", "dt_ms": dt_ms()}
