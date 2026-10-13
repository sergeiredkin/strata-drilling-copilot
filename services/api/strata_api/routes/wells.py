"""`/wells*` routes — contracts/endpoints.yaml's P0 well-scoped endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response
from strata_pipeline.contracts import (
    DdrActivity,
    DepthTimeBlock,
    IltReport,
    KpiReport,
    Mismatch,
    RigStateInterval,
    Section,
    SeriesIndex,
    WellList,
)

from ..data_access import assemble_channel_level, read_json, require_well
from ..deps import SafeIdPath, SettingsDep

router = APIRouter(prefix="/wells", tags=["wells"])


@router.get("", response_model=WellList)
def list_wells(settings: SettingsDep) -> WellList:
    return WellList.model_validate(read_json(settings, "wells.json"))


@router.get("/{well_id}/sections", response_model=list[Section])
def well_sections(well_id: SafeIdPath, settings: SettingsDep) -> list[Section]:
    require_well(settings, well_id)
    return [Section.model_validate(s) for s in read_json(settings, f"wells/{well_id}/sections.json")]


@router.get("/{well_id}/depthtime", response_model=DepthTimeBlock)
def well_depthtime(well_id: SafeIdPath, settings: SettingsDep) -> DepthTimeBlock:
    require_well(settings, well_id)
    return DepthTimeBlock.model_validate(read_json(settings, f"wells/{well_id}/depthtime.json"))


@router.get("/{well_id}/series", response_model=SeriesIndex)
def well_series_index(well_id: SafeIdPath, settings: SettingsDep) -> SeriesIndex:
    require_well(settings, well_id)
    return SeriesIndex.model_validate(read_json(settings, f"wells/{well_id}/series/index.json"))


@router.get("/{well_id}/channels")
def well_channel(
    well_id: SafeIdPath,
    settings: SettingsDep,
    ch: Annotated[str, Query()],
    level: Annotated[int, Query()],
) -> Response:
    """Binary STRS block — docs/04_DATA_CONTRACTS.md §4. Not JSON: `response_model` doesn't apply
    here, the body is raw little-endian bytes decoded client-side by `seriesDecoder.ts`."""
    require_well(settings, well_id)
    body = assemble_channel_level(settings, well_id, ch, level)
    return Response(content=body, media_type="application/octet-stream")


@router.get("/{well_id}/rigstate", response_model=list[RigStateInterval])
def well_rigstate(
    well_id: SafeIdPath,
    settings: SettingsDep,
    start: Annotated[float | None, Query()] = None,
    end: Annotated[float | None, Query()] = None,
) -> list[RigStateInterval]:
    require_well(settings, well_id)
    rows = read_json(settings, f"wells/{well_id}/rigstate.json")
    if start is not None and end is not None:
        rows = [r for r in rows if r["t1"] > start and r["t0"] < end]
    return [RigStateInterval.model_validate(r) for r in rows]


@router.get("/{well_id}/ddr", response_model=list[DdrActivity])
def well_ddr(
    well_id: SafeIdPath,
    settings: SettingsDep,
    start: Annotated[float | None, Query()] = None,
    end: Annotated[float | None, Query()] = None,
) -> list[DdrActivity]:
    require_well(settings, well_id)
    rows = read_json(settings, f"wells/{well_id}/ddr.json")
    if start is not None and end is not None:
        rows = [r for r in rows if r["t1"] > start and r["t0"] < end]
    return [DdrActivity.model_validate(r) for r in rows]


@router.get("/{well_id}/mismatches", response_model=list[Mismatch])
def well_mismatches(well_id: SafeIdPath, settings: SettingsDep) -> list[Mismatch]:
    require_well(settings, well_id)
    return [Mismatch.model_validate(m) for m in read_json(settings, f"wells/{well_id}/mismatches.json")]


@router.get("/{well_id}/kpis", response_model=KpiReport)
def well_kpis(well_id: SafeIdPath, settings: SettingsDep) -> KpiReport:
    require_well(settings, well_id)
    return KpiReport.model_validate(read_json(settings, f"wells/{well_id}/kpis.json"))


@router.get("/{well_id}/ilt", response_model=IltReport)
def well_ilt(well_id: SafeIdPath, settings: SettingsDep) -> IltReport:
    require_well(settings, well_id)
    return IltReport.model_validate(read_json(settings, f"wells/{well_id}/ilt.json"))
