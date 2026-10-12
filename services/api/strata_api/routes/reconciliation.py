"""`/reconciliation` — contracts/endpoints.yaml: `?well=<id>` serves `reconciliation/{id}.json`,
no query serves the cross-well `reconciliation/all.json`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from strata_pipeline.contracts import Reconciliation

from ..data_access import read_json
from ..deps import SettingsDep

router = APIRouter(tags=["reconciliation"])


@router.get("/reconciliation", response_model=Reconciliation)
def reconciliation(settings: SettingsDep, well: Annotated[str | None, Query()] = None) -> Reconciliation:
    path = f"reconciliation/{well}.json" if well else "reconciliation/all.json"
    return Reconciliation.model_validate(read_json(settings, path))
