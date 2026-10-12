"""`/evidence/{id}` — looks up the shard map then the shard file, per
docs/04_DATA_CONTRACTS.md §3's `evidence/shards.json` + `evidence/{00..ff}.json` layout."""

from __future__ import annotations

from fastapi import APIRouter
from strata_pipeline.contracts import Evidence

from ..data_access import read_evidence
from ..deps import SettingsDep

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{evidence_id}", response_model=Evidence)
def evidence(evidence_id: str, settings: SettingsDep) -> Evidence:
    return Evidence.model_validate(read_evidence(settings, evidence_id))
