from strata_pipeline.events.extract import extract_issues, find_event_candidates
from strata_pipeline.evidence import EvidenceRegistry


def test_find_event_candidates_matches_each_lexicon_cluster() -> None:
    assert {c.issue_type for c in find_event_candidates("pipe stuck, worked pipe free")} == {"stuck_pipe"}
    assert {c.issue_type for c in find_event_candidates("5 Ton overpull observed")} == {"tight_hole"}
    assert {c.issue_type for c in find_event_candidates("packed off while reaming")} == {"pack_off"}
    assert {c.issue_type for c in find_event_candidates("losses of 3 m3/h, pumped LCM")} == {"losses"}
    assert {c.issue_type for c in find_event_candidates("gas kick, influx observed")} == {"kick"}


def test_find_event_candidates_returns_empty_for_routine_narrative() -> None:
    assert find_event_candidates("Drilled 12 1/4 hole from 2500 to 2600 m, normal parameters.") == []


def test_find_event_candidates_can_match_more_than_one_cluster() -> None:
    types = {c.issue_type for c in find_event_candidates("tight hole, packed off, worked pipe free")}
    assert types == {"tight_hole", "pack_off", "stuck_pipe"}


def _row(id_: str, t0: int, t1: int, narrative: str, md: float | None = None) -> dict:
    return {
        "id": id_,
        "t0": t0,
        "t1": t1,
        "narrative": narrative,
        "md_from": md,
        "report_date": "2013-05-20",
    }


def test_extract_issues_produces_one_issue_per_matched_candidate() -> None:
    rows = [_row("ddr_W1_0", 1000, 1000 + 3_600_000, "Observed overpull, worked pipe free.", md=2600.0)]
    issues = extract_issues("W1", rows, EvidenceRegistry())
    assert {i["type"] for i in issues} == {"tight_hole", "stuck_pipe"}
    for i in issues:
        assert i["ddr_activity_ids"] == ["ddr_W1_0"]
        assert i["extraction"] == "rule"
        assert i["md"] == 2600.0


def test_extract_issues_skips_rows_with_no_lexicon_match() -> None:
    rows = [_row("ddr_W1_0", 1000, 2000, "Drilled 50 m of 8 1/2 hole, no issues.")]
    assert extract_issues("W1", rows, EvidenceRegistry()) == []


def test_extract_issues_computes_duration_as_a_quantity() -> None:
    rows = [_row("ddr_W1_0", 0, 7_200_000, "Stuck pipe.")]
    issues = extract_issues("W1", rows, EvidenceRegistry())
    assert issues[0]["duration"]["value"] == 120.0
    assert issues[0]["duration"]["unit"] == "min"
    assert issues[0]["duration"]["evidence_id"].startswith("ev_")


def test_extract_issues_resolves_formation_from_tops_when_given() -> None:
    rows = [_row("ddr_W1_0", 0, 1000, "Stuck pipe.", md=2650.0)]
    formations = {"tops": [{"name": "Draupne Fm.", "md_top": 2600.0, "md_base": 2700.0}]}
    issues = extract_issues("W1", rows, EvidenceRegistry(), formations=formations)
    assert issues[0]["formation"] == "Draupne Fm."


def test_extract_issues_formation_is_null_without_md_or_formations() -> None:
    rows = [_row("ddr_W1_0", 0, 1000, "Stuck pipe.", md=None)]
    issues = extract_issues("W1", rows, EvidenceRegistry())
    assert issues[0]["formation"] is None
