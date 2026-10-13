"""Ablation runner — docs/02_IMPLEMENTATION_PLAN.md T9.2, docs/07_DATA_AND_ALGORITHMS.md §13.
Runs every gold question through four agent configurations and returns one raw result per
(question, config) pair; `score.py` turns those into the `EvalReport.ablation` metrics.

The real run only matters once `eval/gold/questions.yaml`'s `status` is `final` (>= 25 real
questions, Sergei's call) — until then this is exercised only by a 3-question smoke test with a
fake LLM client (docs/02_IMPLEMENTATION_PLAN.md T9.2's acceptance criterion).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from strata_api.copilot.agent import LlmClient, run_agent
from strata_api.copilot.tools import TOOL_SPECS
from strata_api.settings import Settings
from strata_pipeline.contracts import CopilotContext

AblationConfig = Literal["no_tools", "simple_rag", "full", "full_minus_physics"]
ABLATION_CONFIGS: list[AblationConfig] = ["no_tools", "simple_rag", "full", "full_minus_physics"]

ALL_TOOL_NAMES = {spec["name"] for spec in TOOL_SPECS}
# "physics" tools derive from sensor/classifier output or a DDR-vs-sensor comparison — see
# docs/adr/0008-copilot-tool-signatures.md decision 4 for why these specifically.
PHYSICS_TOOLS = {
    "rigstate_summary", "kpi_connection_times", "kpi_trips", "ilt_breakdown",
    "formation_stats", "reconciliation", "mismatches",
}


@dataclass(frozen=True)
class ExpectedNumber:
    value: float | None = None
    unit: str | None = None
    tolerance: float | None = None
    evidence_id: str | None = None


@dataclass(frozen=True)
class GoldQuestion:
    id: str
    question: str
    context: CopilotContext
    expected_kind: Literal["answer", "insufficient_data", "out_of_scope"]
    expected_numbers: list[ExpectedNumber]
    rubric_notes: str | None = None


@dataclass(frozen=True)
class GoldSetMeta:
    status: Literal["pending", "draft", "final"]
    version: str
    author: str
    n_questions: int


def load_gold(path: Path) -> tuple[GoldSetMeta, list[GoldQuestion]]:
    """`n_questions` excludes any `EXAMPLE-`-prefixed entry (see questions.yaml's header
    comment) — those document the schema, they are not gold data."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = [
        GoldQuestion(
            id=q["id"],
            question=q["question"],
            context=CopilotContext.model_validate(q["context"]),
            expected_kind=q["expected_kind"],
            expected_numbers=[ExpectedNumber(**n) for n in q.get("expected_numbers", [])],
            rubric_notes=q.get("rubric_notes"),
        )
        for q in raw.get("questions", [])
    ]
    real_questions = [q for q in questions if not q.id.startswith("EXAMPLE-")]
    meta = GoldSetMeta(
        status=raw["status"], version=raw["version"], author=raw["author"], n_questions=len(real_questions)
    )
    return meta, questions


def _simple_rag_context(question: GoldQuestion, settings: Settings) -> str:
    """A crude retrieval-augmented context dump: BM25-retrieved DDR narratives plus the well's
    raw kpis/ilt JSON as text, handed to the model with no tool access at all — the `simple_rag`
    baseline docs/07_DATA_AND_ALGORITHMS.md §13 asks for."""
    from strata_api.copilot.tools import CopilotTools
    from strata_pipeline.evidence import EvidenceRegistry

    well = question.context.well
    if well is None:
        return "No well selected; no retrieved context available."
    tools = CopilotTools(settings, EvidenceRegistry(git_commit="eval"))
    parts = [f"Retrieved context for well {well}:"]
    try:
        ddr_hits = tools.ddr_search(str(well), question.question, top_k=5)
        parts.append("DDR narratives:\n" + "\n".join(r["narrative"] for r in ddr_hits["results"]))
    except Exception:  # noqa: BLE001 - best-effort context, never fatal to the run
        pass
    for tool_name in ("ilt_breakdown",):
        try:
            parts.append(f"{tool_name}: {getattr(tools, tool_name)(str(well), 'category')}")
        except Exception:  # noqa: BLE001
            pass
    return "\n\n".join(parts)


async def run_one(
    question: GoldQuestion,
    config: AblationConfig,
    settings: Settings,
    client: LlmClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    allowed_tools: set[str] | None
    extra_context: str | None = None
    if config == "full":
        allowed_tools = None
    elif config == "full_minus_physics":
        allowed_tools = ALL_TOOL_NAMES - PHYSICS_TOOLS
    elif config == "no_tools":
        allowed_tools = set()
    elif config == "simple_rag":
        allowed_tools = set()
        extra_context = _simple_rag_context(question, settings)

    t0 = time.monotonic()
    events = [
        event
        async for event in run_agent(
            question=question.question,
            context=question.context,
            settings=settings,
            session_id=f"eval_{config}_{question.id}",
            client=client,
            model=model,
            allowed_tools=allowed_tools,
            extra_context=extra_context,
        )
    ]
    elapsed_s = time.monotonic() - t0

    answer_event = next((e for e in events if e["type"] == "answer"), None)
    error_event = next((e for e in events if e["type"] == "error"), None)
    return {
        "question_id": question.id,
        "config": config,
        "expected_kind": question.expected_kind,
        "expected_numbers": question.expected_numbers,
        "answer": answer_event["answer"] if answer_event else None,
        "error": error_event["message"] if error_event else None,
        "elapsed_s": elapsed_s,
    }


async def run_all(
    questions: list[GoldQuestion],
    settings: Settings,
    client: LlmClient | None = None,
    model: str | None = None,
    configs: list[AblationConfig] | None = None,
) -> list[dict[str, Any]]:
    results = []
    for question in questions:
        for config in configs or ABLATION_CONFIGS:
            results.append(await run_one(question, config, settings, client, model))
    return results
