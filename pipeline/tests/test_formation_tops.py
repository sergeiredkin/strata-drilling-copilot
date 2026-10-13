from pathlib import Path

from strata_pipeline.ingest.formation_tops import load_well_picks_csv, picks_for_wellbore

SAMPLE_CSV = Path(__file__).parent / "samples" / "volve_well_picks" / "sample_picks.csv"


def test_load_well_picks_csv_reads_every_row() -> None:
    rows = load_well_picks_csv(SAMPLE_CSV)
    assert len(rows) == 30  # 16 for F-1 C + 14 for F-11 A, per the sample file


def test_picks_for_wellbore_filters_and_sorts_by_depth() -> None:
    rows = load_well_picks_csv(SAMPLE_CSV)
    picks = picks_for_wellbore(rows, "15/9-F-11 A")
    assert len(picks) == 14
    mds = [p.md for p in picks]
    assert mds == sorted(mds)
    assert picks[0].name in {"NORDLAND GP. Top", "Seabed"}  # shallowest, tied at 146 m
    assert picks[-1].name in {"Hugin Fm. VOLVE Base", "Sleipner Fm. Top"}  # deepest, tied at 3702 m


def test_picks_for_wellbore_matches_the_csvs_no_prefixed_name() -> None:
    # The CSV's raw WELL column is "NO 15/9-F-11 A"; callers pass the plain wellbore name
    # (export/real_wells.py's style) and the "NO " prefix must not need repeating.
    rows = load_well_picks_csv(SAMPLE_CSV)
    assert picks_for_wellbore(rows, "15/9-F-11 A") == picks_for_wellbore(rows, "NO 15/9-F-11 A")


def test_picks_for_wellbore_does_not_cross_contaminate_wells() -> None:
    rows = load_well_picks_csv(SAMPLE_CSV)
    picks = picks_for_wellbore(rows, "15/9-F-1 C")
    assert all(p.md <= 4003.9 for p in picks)  # F-1 C's deepest pick; F-11 A goes to 3702 but
    # that's within range too -- the real assertion is count, not a depth bound:
    assert len(picks) == 16


def test_picks_for_wellbore_unknown_well_returns_empty() -> None:
    rows = load_well_picks_csv(SAMPLE_CSV)
    assert picks_for_wellbore(rows, "99/9-Z-99") == []


def test_picks_for_wellbore_keeps_repeated_names_at_different_depths() -> None:
    # "Hugin Fm. VOLVE Top"/"Base" repeats 3x in F-1 C (a faulted repeat section) -- these are
    # real, distinct picks and must not be deduplicated away.
    rows = load_well_picks_csv(SAMPLE_CSV)
    picks = picks_for_wellbore(rows, "15/9-F-1 C")
    hugin_tops = [p for p in picks if p.name == "Hugin Fm. VOLVE Top"]
    assert len(hugin_tops) == 2
    assert {p.md for p in hugin_tops} == {3229.5, 3853.7}
