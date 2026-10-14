"""`WS /replay/{well_id}` — T13.2, docs/03_ARCHITECTURE.md §4: "server streams L0 samples +
state transitions + alert events at speed." The merge/decode logic lives in `../replay.py`
(plain generator, testable without a socket); this route only adds the real-time-scaled delay
(same convention as the static client's `playReplay`, capped at 1.5s) and the WebSocket itself.
"""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ..deps import SAFE_ID_PATTERN, get_settings
from ..replay import merge_replay_events

router = APIRouter(tags=["replay"])

_VALID_SPEEDS = {1, 10, 60}
_MAX_DELAY_S = 1.5
_SAFE_ID_RE = re.compile(SAFE_ID_PATTERN)


@router.websocket("/replay/{well_id}")
async def replay_ws(websocket: WebSocket, well_id: str) -> None:
    if not _SAFE_ID_RE.match(well_id):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    settings = get_settings()

    try:
        speed = int(websocket.query_params.get("speed", "1"))
    except ValueError:
        speed = 1
    if speed not in _VALID_SPEEDS:
        speed = 1
    try:
        from_t = float(websocket.query_params.get("from_t", "0"))
    except ValueError:
        from_t = 0.0

    last_t: float | None = None
    try:
        for event in merge_replay_events(settings, well_id, from_t):
            if websocket.client_state != WebSocketState.CONNECTED:
                break
            if last_t is not None:
                delay_s = min((event["t"] - last_t) / speed / 1000.0, _MAX_DELAY_S)
                if delay_s > 0:
                    await asyncio.sleep(delay_s)
            last_t = event["t"]
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    await websocket.close()
