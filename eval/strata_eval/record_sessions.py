"""`python -m strata_eval.record_sessions` — docs/02_IMPLEMENTATION_PLAN.md T8.5: runs the real
copilot agent (services/api/strata_api/copilot/agent.py) against the demo questions below and
records each one into `data/export/copilot/sessions/` via the recorder, so static mode replays a
genuine live-mode run instead of (or alongside) the T1.2 fixture generator's synthesized ones.

Needs `ANTHROPIC_API_KEY` set (and optionally `STRATA_LLM_MODEL`) — this makes a real, billed LLM
call per question. Only `DEMO_QUESTIONS` below is seeded: the one demo question
docs/08_TESTING_AND_ACCEPTANCE.md §3 names literally ("What drove the lost time in the 12¼″
section?"). The broader S4 suggestion catalogue is Sergei's content call (same as the copilot
gold question set) — add more `DemoQuestion` entries here rather than inventing them elsewhere.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from strata_api.copilot.agent import LlmClient, run_agent
from strata_api.copilot.recorder import record_session
from strata_api.settings import Settings
from strata_pipeline.contracts import CopilotContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _REPO_ROOT / "apps" / "web" / "public" / "data"


@dataclass(frozen=True)
class DemoQuestion:
    session_id: str
    question: str
    context: CopilotContext


DEMO_QUESTIONS: list[DemoQuestion] = [
    DemoQuestion(
        session_id="s4_lost_time_12_1_4",
        question='What drove the lost time in the 12¼″ section?',
        context=CopilotContext(screen="performance", well="15_9-F-11_A", section="12¼"),
    ),
]


async def record_one(
    question: DemoQuestion, settings: Settings, model: str | None, client: LlmClient | None = None
) -> dict[str, object]:
    events = [
        event
        async for event in run_agent(
            question=question.question,
            context=question.context,
            settings=settings,
            session_id=question.session_id,
            model=model,
            client=client,
        )
    ]
    return record_session(
        settings.data_dir,
        question.session_id,
        question.question,
        question.context,
        model or os.environ.get("STRATA_LLM_MODEL", "claude-sonnet-5-5"),
        events,
    )


async def main_async(
    data_dir: Path, model: str | None, client: LlmClient | None = None, questions: list[DemoQuestion] | None = None
) -> int:
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set — recording a real session needs a live LLM call.", file=sys.stderr)
        return 1
    settings = Settings(data_dir=data_dir, cors_origins=[])
    for question in questions if questions is not None else DEMO_QUESTIONS:
        entry = await record_one(question, settings, model, client)
        print(f"recorded {entry['id']} -> {entry['file']}")
    return 0


def main() -> None:
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args.data_dir, args.model)))


if __name__ == "__main__":
    main()
