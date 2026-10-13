"""Unit tests for copilot/tools.py against the repo's own committed fixture export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from strata_api.copilot.tools import CopilotTools, ToolError
from strata_api.settings import Settings
from strata_pipeline.evidence import EvidenceRegistry

FIXTURE_DATA_DIR = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "data"
WELL = "15_9-F-11_A"


@pytest.fixture
def tools() -> CopilotTools:
    settings = Settings(data_dir=FIXTURE_DATA_DIR, cors_origins=[])
    return CopilotTools(settings, EvidenceRegistry(git_commit="test"))


@pytest.fixture
def well_span() -> tuple[float, float]:
    """The well's actual rigstate span, read fresh rather than hardcoded — this well's export
    can be mock or real depending on what's currently committed (docs/02_IMPLEMENTATION_PLAN.md
    T10.4)."""
    rows = json.loads((FIXTURE_DATA_DIR / "wells" / WELL / "rigstate.json").read_text())
    return min(r["t0"] for r in rows), max(r["t1"] for r in rows)


def test_list_wells_includes_the_fixture_well(tools: CopilotTools) -> None:
    result = tools.list_wells()
    assert any(w["id"] == WELL for w in result["wells"])


def test_well_summary_unknown_well_raises_tool_error(tools: CopilotTools) -> None:
    with pytest.raises(ToolError):
        tools.well_summary("not-a-real-well")


def test_rigstate_summary_mints_evidence_with_the_sum_of_overlapping_intervals(
    tools: CopilotTools, well_span: tuple[float, float]
) -> None:
    t0, t1 = well_span
    result = tools.rigstate_summary(WELL, t0, t1)
    assert result["n_intervals"] > 0
    assert "rotary_drilling" in result["by_state"]
    rotary = result["by_state"]["rotary_drilling"]
    assert rotary["unit"] == "h"
    assert rotary["value"] > 0
    # The minted evidence id resolves back through the same registry (ADR 0008 decision 2).
    record = tools.evidence(rotary["evidence_id"])
    assert record["value"] == rotary["value"]


def test_rigstate_summary_partial_overlap_is_clipped_to_the_window(
    tools: CopilotTools, well_span: tuple[float, float]
) -> None:
    # A window covering only the first half of the well's span must not count the second half.
    t0, t1 = well_span
    midpoint = t0 + (t1 - t0) / 2
    full = tools.rigstate_summary(WELL, t0, t1)
    half = tools.rigstate_summary(WELL, t0, midpoint)
    full_rotary = full["by_state"].get("rotary_drilling", {}).get("value", 0.0)
    half_rotary = half["by_state"].get("rotary_drilling", {}).get("value", 0.0)
    assert half_rotary <= full_rotary


def test_kpi_connection_times_bad_stat_raises_tool_error(tools: CopilotTools) -> None:
    with pytest.raises(ToolError):
        tools.kpi_connection_times(WELL, "well", "median")


def test_kpi_connection_times_well_level(tools: CopilotTools) -> None:
    result = tools.kpi_connection_times(WELL, "well", "s2s")
    assert result["kpi"] == "conn_s2s"
    assert "value" in result and "best" in result


def test_kpi_trips_bad_direction_raises_tool_error(tools: CopilotTools) -> None:
    with pytest.raises(ToolError):
        tools.kpi_trips(WELL, "well", "sideways", "open")


def test_ilt_breakdown_by_category(tools: CopilotTools) -> None:
    result = tools.ilt_breakdown(WELL, "category")
    assert "category" in result
    assert isinstance(result["category"], list)


def test_ddr_search_finds_a_matching_narrative(tools: CopilotTools) -> None:
    result = tools.ddr_search(WELL, "pulled out of hole")
    assert result["results"], "expected at least one BM25 match"
    assert "pulled" in result["results"][0]["narrative"].lower()


def test_ddr_search_no_match_returns_empty_results(tools: CopilotTools) -> None:
    # Gibberish with no real word fragments at all — unlike a made-up phrase built from ordinary
    # English words (a prior version of this test used "xyzxyzxyz_no_such_term", which still
    # BM25-matched on "no"/"such"/"term" once real DDR narratives replaced the mock ones).
    result = tools.ddr_search(WELL, "qzxjklvwqz9999 zxcvbnmqwer8888")
    assert result["results"] == []


def test_formation_stats_unavailable_raises_tool_error(tools: CopilotTools) -> None:
    # T11.x (formation classifier export) isn't built yet — this must be an honest tool error,
    # not a crash or a fabricated stat.
    with pytest.raises(ToolError):
        tools.formation_stats(WELL, "Hugin")


def test_issues_query_empty_fixture_returns_empty_list(tools: CopilotTools) -> None:
    result = tools.issues_query(well=WELL)
    assert result["issues"] == []


def test_evidence_unknown_id_raises_tool_error(tools: CopilotTools) -> None:
    with pytest.raises(ToolError):
        tools.evidence("ev_0000000000")
