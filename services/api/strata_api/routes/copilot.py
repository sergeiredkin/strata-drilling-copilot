"""`/copilot/sessions` and `/copilot/ask` — docs/02_IMPLEMENTATION_PLAN.md T8.4. `ask` runs the
real agent loop (`copilot/agent.py`): an Anthropic Messages API tool-use loop over
`copilot/tools.py`, ending when the model calls `submit_answer`, verified by
`copilot/verifier.py` before being streamed back. Every intermediate tool call is also streamed
as its own `CopilotEvent` so a live client can show progress, not just the final answer.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from strata_pipeline.contracts import CopilotContext

from ..copilot.agent import run_agent
from ..data_access import read_json
from ..deps import SettingsDep

router = APIRouter(prefix="/copilot", tags=["copilot"])


class AskRequest(BaseModel):
    question: str
    context: CopilotContext
    session_id: str | None = None


@router.get("/sessions")
def sessions(settings: SettingsDep) -> dict[str, Any]:
    return read_json(settings, "copilot/sessions/index.json")  # type: ignore[no-any-return]


@router.post("/ask")
async def ask(request: AskRequest, settings: SettingsDep) -> EventSourceResponse:
    session_id = request.session_id or f"live_{uuid.uuid4().hex[:12]}"

    async def events() -> AsyncIterator[dict[str, Any]]:
        async for event in run_agent(
            question=request.question, context=request.context, settings=settings, session_id=session_id
        ):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(events())
