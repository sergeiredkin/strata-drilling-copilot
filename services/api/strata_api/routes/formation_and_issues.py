"""P1/P2 routes from contracts/endpoints.yaml. None of these static files are produced by the
pipeline yet (formation classifier is T11.x, events/issues is T12.x) — the routes exist so the
contract is honoured end-to-end, but every one 404s honestly via `read_json` until that data
exists, rather than being silently absent from the API."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from strata_pipeline.contracts import FormationPrediction, FormationReport, Issue, ModelCard, Precursors

from ..data_access import read_json, require_well
from ..deps import SafeIdPath, SettingsDep

router = APIRouter(tags=["formation", "issues"])


@router.get("/wells/{well_id}/formations", response_model=FormationReport)
def formations(well_id: SafeIdPath, settings: SettingsDep) -> FormationReport:
    require_well(settings, well_id)
    return FormationReport.model_validate(read_json(settings, f"wells/{well_id}/formations.json"))


@router.get("/wells/{well_id}/formation-pred", response_model=FormationPrediction)
def formation_pred(well_id: SafeIdPath, settings: SettingsDep) -> FormationPrediction:
    require_well(settings, well_id)
    return FormationPrediction.model_validate(read_json(settings, f"wells/{well_id}/formation_pred.json"))


@router.get("/models/{model}/card", response_model=ModelCard)
def model_card(model: Literal["formation", "events"], settings: SettingsDep) -> ModelCard:
    return ModelCard.model_validate(read_json(settings, f"models/{model}_card.json"))


@router.get("/issues", response_model=list[Issue])
def issues(
    settings: SettingsDep,
    well: Annotated[str | None, Query()] = None,
    type: Annotated[str | None, Query()] = None,  # noqa: A002 - matches the contract's query name
    formation: Annotated[str | None, Query()] = None,
) -> list[Issue]:
    rows = read_json(settings, "issues.json")
    if well is not None:
        rows = [r for r in rows if r.get("well") == well]
    if type is not None:
        rows = [r for r in rows if r.get("type") == type]
    if formation is not None:
        rows = [r for r in rows if r.get("formation") == formation]
    return [Issue.model_validate(r) for r in rows]


@router.get("/issues/{issue_id}/precursors", response_model=Precursors)
def precursors(issue_id: SafeIdPath, settings: SettingsDep) -> Precursors:
    return Precursors.model_validate(read_json(settings, f"issues/{issue_id}_precursors.json"))
