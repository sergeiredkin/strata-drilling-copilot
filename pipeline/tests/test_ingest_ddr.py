from pathlib import Path

from strata_pipeline.ingest.ddr import (
    load_well_bit_runs,
    load_well_ddr,
    normalize_code,
    parse_bit_runs,
    parse_ddr_file,
)

SAMPLE_DIR = Path(__file__).parent / "samples" / "volve_15_9-F-11_A" / "ddr"


def test_normalize_code_known_prefixes():
    assert normalize_code("Drilling -- Drill") == "DRILL"
    assert normalize_code("Drilling -- Circulating") == "CIRC"
    assert normalize_code("Drilling -- Trip") == "TRIP"
    assert normalize_code("Drilling -- Ream") == "REAM"
    assert normalize_code("Drilling -- Casing") == "CASING"
    assert normalize_code("Drilling -- BOP") == "BOP"
    assert normalize_code("Plug Abandon -- Cement") == "CEMENT"
    assert normalize_code("Interruption -- Weather") == "WAIT"


def test_normalize_code_unknown_falls_back_to_other():
    assert normalize_code("Completion -- Perforating") == "OTHER"
    assert normalize_code("") == "OTHER"


def test_parse_ddr_file_real_day():
    rows = parse_ddr_file(SAMPLE_DIR / "15_9_F_11_A_2013_05_15.xml")
    assert len(rows) > 0
    for row in rows:
        assert row["t0"].tzinfo is not None
        assert row["t0"] <= row["t1"]
        assert row["normalized_code"] in {
            "DRILL", "CIRC", "TRIP", "REAM", "CASING", "CEMENT", "BOP", "WAIT", "OTHER",
        }


def test_parse_ddr_file_converts_local_time_to_utc():
    # 2013-05-15 is CEST (+02:00) in Norway.
    rows = parse_ddr_file(SAMPLE_DIR / "15_9_F_11_A_2013_05_15.xml")
    assert rows
    for row in rows:
        assert row["t0"].utcoffset().total_seconds() == 0
        assert row["t1"].utcoffset().total_seconds() == 0


def test_load_well_ddr_concatenates_and_sorts_both_sample_days():
    df = load_well_ddr(SAMPLE_DIR, "15_9_F_11_A")
    assert len(df) > 0
    t0 = df["t0"].to_list()
    assert t0 == sorted(t0)
    # report_date comes from each file's own dTimStart, which starts at local midnight the day
    # before the filename's date (e.g. the "..._2013_05_15.xml" report starts 2013-05-14T00:00).
    assert set(df["report_date"].unique()) == {"2013-05-14", "2013-05-24"}


def test_load_well_ddr_missing_well_returns_empty_frame():
    df = load_well_ddr(SAMPLE_DIR, "99_9_Z_99_Z")
    assert len(df) == 0
    assert "normalized_code" in df.columns


def test_parse_bit_runs_real_day_with_a_bit_record():
    # Real F-11 A bit record: 8.5 in bit drilled 2586 -> 3762 m MD.
    rows = parse_bit_runs(SAMPLE_DIR / "15_9_F_11_A_2013_05_25.xml")
    assert rows == [{"report_date": "2013-05-24", "diameter_in": 8.5, "md_top": 2586.0, "md_base": 3762.0}]


def test_parse_bit_runs_day_without_a_bit_record_is_empty():
    rows = parse_bit_runs(SAMPLE_DIR / "15_9_F_11_A_2013_05_15.xml")
    assert rows == []


def test_load_well_bit_runs_concatenates_across_days():
    rows = load_well_bit_runs(SAMPLE_DIR, "15_9_F_11_A")
    assert rows == [{"report_date": "2013-05-24", "diameter_in": 8.5, "md_top": 2586.0, "md_base": 3762.0}]


def test_load_well_bit_runs_missing_well_returns_empty_list():
    assert load_well_bit_runs(SAMPLE_DIR, "99_9_Z_99_Z") == []
