import sys

import pytest
from strata_pipeline.export import cli


def test_resolve_well_exits_on_unknown_id(capsys):
    with pytest.raises(SystemExit) as exc:
        cli._resolve_well("not-a-real-well")
    assert exc.value.code == 1
    assert "Unknown well id" in capsys.readouterr().err


def test_resolve_well_returns_matching_spec():
    spec = cli._resolve_well("15_9-F-11_A")
    assert spec.wellbore_name == "15/9-F-11 A"


def test_require_raw_data_exits_when_archive_missing(monkeypatch, capsys):
    monkeypatch.setattr(cli, "raw_data_available", lambda: False)
    with pytest.raises(SystemExit) as exc:
        cli._require_raw_data()
    assert exc.value.code == 1
    assert "Raw Volve archive not found" in capsys.readouterr().err


def test_require_raw_data_passes_when_archive_present(monkeypatch):
    monkeypatch.setattr(cli, "raw_data_available", lambda: True)
    cli._require_raw_data()  # must not raise


def test_pipeline_main_exits_before_running_well_if_archive_missing(monkeypatch):
    monkeypatch.setattr(cli, "raw_data_available", lambda: False)
    monkeypatch.setattr(sys, "argv", ["prog", "--well", "15_9-F-11_A"])
    called = []
    monkeypatch.setattr(cli, "run_well", lambda *a, **k: called.append(True))
    with pytest.raises(SystemExit):
        cli.pipeline_main()
    assert not called


def test_export_main_exits_before_generating_if_archive_missing(monkeypatch):
    monkeypatch.setattr(cli, "raw_data_available", lambda: False)
    called = []
    monkeypatch.setattr(cli, "generate_real", lambda *a, **k: called.append(True))
    with pytest.raises(SystemExit):
        cli.export_main()
    assert not called


def test_reproduce_main_reports_mismatch_and_exits_nonzero(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "raw_data_available", lambda: True)
    monkeypatch.setattr(sys, "argv", ["prog", "--well", "15_9-F-11_A"])

    call_count = {"n": 0}

    def fake_run_well(well_id, witsml_root, wellbore_name, ddr_dir, ddr_file_prefix, out_dir, reg, *a, **k):
        call_count["n"] += 1
        (out_dir).mkdir(parents=True, exist_ok=True)
        (out_dir / "f.json").write_text(f"run{call_count['n']}")

    monkeypatch.setattr(cli, "run_well", fake_run_well)
    with pytest.raises(SystemExit) as exc:
        cli.reproduce_main()
    assert exc.value.code == 1
    assert "NOT reproducible" in capsys.readouterr().err


def test_reproduce_main_reports_success_when_identical(monkeypatch, capsys):
    monkeypatch.setattr(cli, "raw_data_available", lambda: True)
    monkeypatch.setattr(sys, "argv", ["prog", "--well", "15_9-F-11_A"])

    def fake_run_well(well_id, witsml_root, wellbore_name, ddr_dir, ddr_file_prefix, out_dir, reg, *a, **k):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "f.json").write_text("same")

    monkeypatch.setattr(cli, "run_well", fake_run_well)
    cli.reproduce_main()
    out = capsys.readouterr().out
    assert '"reproducible": true' in out
