"""`/eval` and `/meta/repro` — top-level static files, no path params."""

from __future__ import annotations

from fastapi import APIRouter
from strata_pipeline.contracts import EvalReport, ReproManifest

from ..data_access import read_json
from ..deps import SettingsDep

router = APIRouter(tags=["meta"])


@router.get("/eval", response_model=EvalReport)
def eval_report(settings: SettingsDep) -> EvalReport:
    return EvalReport.model_validate(read_json(settings, "eval.json"))


@router.get("/meta/repro", response_model=ReproManifest)
def repro_manifest(settings: SettingsDep) -> ReproManifest:
    return ReproManifest.model_validate(read_json(settings, "repro.json"))
