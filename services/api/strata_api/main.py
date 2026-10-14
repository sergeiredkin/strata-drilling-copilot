"""FastAPI app — T8.3 live mode. Serves `data/export/**` per contracts/endpoints.yaml; never
recomputes analytics on request (docs/03_ARCHITECTURE.md §2), so static and live mode show
identical numbers for the same export."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import get_settings
from .routes import copilot, evidence, formation_and_issues, meta, reconciliation, replay, wells

app = FastAPI(title="STRATA API", version="0.2.0")

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(wells.router)
app.include_router(reconciliation.router)
app.include_router(evidence.router)
app.include_router(meta.router)
app.include_router(copilot.router)
app.include_router(formation_and_issues.router)
app.include_router(replay.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
