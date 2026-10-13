from pathlib import Path

import numpy as np
from strata_pipeline.formation.labels import FormationInterval, label_bins, tops_to_intervals
from strata_pipeline.ingest.formation_tops import load_well_picks_csv, picks_for_wellbore

SAMPLE_CSV = Path(__file__).parent / "samples" / "volve_well_picks" / "sample_picks.csv"


def _f11a_intervals() -> list[FormationInterval]:
    rows = load_well_picks_csv(SAMPLE_CSV)
    picks = picks_for_wellbore(rows, "15/9-F-11 A")
    return tops_to_intervals(picks)


def test_tops_to_intervals_excludes_group_tops_and_seabed() -> None:
    intervals = _f11a_intervals()
    names = {iv.name for iv in intervals}
    assert "NORDLAND GP. Top" not in names
    assert "HORDALAND GP. Top" not in names
    assert "SHETLAND GP. Top" not in names
    assert "Seabed" not in names


def test_tops_to_intervals_excludes_explicit_base_rows_as_their_own_interval() -> None:
    intervals = _f11a_intervals()
    assert all("Base" not in iv.name for iv in intervals)


def test_tops_to_intervals_consecutive_tops_are_contiguous() -> None:
    intervals = _f11a_intervals()
    ordered = sorted(intervals, key=lambda iv: iv.md_top)
    for a, b in zip(ordered, ordered[1:], strict=False):
        assert a.md_base == b.md_top


def test_tops_to_intervals_drops_the_deepest_pick_with_no_known_base() -> None:
    # F-11 A's deepest formation top is "Sleipner Fm. Top" at 3702.0 -- the base of whatever
    # comes after it isn't known from picks alone, so it must not appear as an interval.
    intervals = _f11a_intervals()
    assert not any(iv.md_top == 3702.0 for iv in intervals)


def test_tops_to_intervals_drops_zero_width_duplicate_depth_picks() -> None:
    # Ekofisk Fm. Top and the Shetland group top coincide at the same depth in the sample --
    # Ekofisk's own interval must still have positive width, not collapse to zero.
    intervals = _f11a_intervals()
    for iv in intervals:
        assert iv.md_base > iv.md_top


def test_tops_to_intervals_strips_the_top_suffix_from_the_label() -> None:
    intervals = _f11a_intervals()
    names = {iv.name for iv in intervals}
    assert "Ty Fm." in names
    assert "Ty Fm. Top" not in names


def test_label_bins_assigns_the_covering_formations_name() -> None:
    intervals = _f11a_intervals()
    md = np.array([2700.0, 2800.0, 3705.0])  # inside Ty Fm, inside Ekofisk Fm, beyond coverage
    labels = label_bins(md, intervals)
    assert labels[0] == "Ty Fm."
    assert labels[1] == "Ekofisk Fm."
    assert labels[2] is None
