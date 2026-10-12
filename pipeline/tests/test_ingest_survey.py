from pathlib import Path

from strata_pipeline.ingest.survey import max_tvd_discrepancy, minimum_curvature, parse_survey_file

SAMPLE_PATH = (
    Path(__file__).parent
    / "samples"
    / "volve_15_9-F-11_A"
    / "survey"
    / "Volve F_F-11_159-F-11 A_159-F-11 A_ACTUAL"
)


def test_minimum_curvature_vertical_well_has_no_horizontal_displacement():
    tvd, north, east = minimum_curvature([0.0, 100.0, 200.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    assert tvd == [0.0, 100.0, 200.0]
    assert north == [0.0, 0.0, 0.0]
    assert east == [0.0, 0.0, 0.0]


def test_minimum_curvature_single_station_is_a_no_op():
    tvd, north, east = minimum_curvature([0.0], [0.0], [0.0])
    assert tvd == [0.0]
    assert north == [0.0]
    assert east == [0.0]


def test_parse_survey_file_real_well_has_expected_station_count():
    df = parse_survey_file(SAMPLE_PATH)
    assert len(df) == 319
    assert df["md"].is_sorted()


def test_parse_survey_file_computed_tvd_matches_reference_within_tolerance():
    df = parse_survey_file(SAMPLE_PATH)
    # docs/07_DATA_AND_ALGORITHMS.md: our minimum-curvature TVD must agree with Statoil's own
    # reference column — validated manually at ~5mm over a 3762m well; keep a generous margin.
    assert max_tvd_discrepancy(df) < 0.01


def test_parse_survey_file_missing_file_raises():
    try:
        parse_survey_file(Path(__file__).parent / "samples" / "does_not_exist")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError for a missing survey file")
