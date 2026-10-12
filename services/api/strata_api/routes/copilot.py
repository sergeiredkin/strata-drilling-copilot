"""`/copilot/sessions` and `/copilot/ask`. The real agent (tools, LLM loop, verifier) is T8.4 —
not built yet. `ask` still honestly answers over SSE with `kind: "live_mode_required"`
(`CopilotAnswer`'s own enum has exactly this value) rather than a bare error or a 404, since a
contract-valid "not available yet" response is what a live-mode client should be able to render
today; T8.4 replaces this handler's body, not its route or wire format.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from strata_pipeline.contracts import CopilotContext

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
async def ask(request: AskRequest) -> EventSourceResponse:
    async def events() -> AsyncIterator[dict[str, Any]]:
        session_id = request.session_id or "live"
        yield {
            "data": json.dumps(
                {"type": "start", "session_id": session_id, "dt_ms": 0, "context": request.context.model_dump()}
            )
        }
        answer = {
            "kind": "live_mode_required",
            "answer": (
                "The live copilot agent isn't implemented yet (T8.4) — "
                "ask in static mode to see recorded demo sessions."
            ),
            "claims": [],
            "ddr_quotes": [],
            "reasoning": "services/api/strata_api/copilot/agent.py has not been built.",
            "assumptions": [],
            "confidence": "low",
            "confidence_reason": "no agent is running; this is a placeholder response.",
            "trace": [],
        }
        yield {"data": json.dumps({"type": "answer", "answer": answer, "dt_ms": 0})}

    return EventSourceResponse(events())
