import numpy as np
from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.formation.depth_features import DepthFeatureTable
from strata_pipeline.formation.labels import FormationInterval
from strata_pipeline.formation.report import build_formation_report, lith_for_formation


def _table() -> DepthFeatureTable:
    md = np.arange(1000.0, 1100.0)
    rop = np.full(100, 15.0)
    rop[50:] = np.nan  # SHALE's ROP is unknown -- stats must stay null, not average in NaN
    return DepthFeatureTable(
        md=md,
        rop_m_per_h=rop,
        wob_kN=np.full(100, 50.0),
        rpm=np.full(100, 120.0),
        torque_kNm=np.full(100, 20.0),
        gas_pct=np.full(100, 2.0),
        mse_mpa=np.full(100, 80.0),
        dxc=np.full(100, 1.2),
        n_samples=np.full(100, 10.0),
    )


def _tops() -> list[FormationInterval]:
    return [
        FormationInterval(name="Ty Fm.", md_top=1000.0, md_base=1050.0),
        FormationInterval(name="Heather Fm.", md_top=1050.0, md_base=1100.0),
    ]


def test_lith_for_formation_known_and_unknown() -> None:
    assert lith_for_formation("Ty Fm.") == "sandstone"
    assert lith_for_formation("Ekofisk Fm.") == "limestone"
    assert lith_for_formation("Some Invented Fm.") == "other"


def test_build_formation_report_shapes_tops_and_lithology() -> None:
    report = build_formation_report("W1", _table(), _tops(), EvidenceRegistry(), source="test.csv")
    assert report["well"] == "W1"
    assert report["tops"] == [
        {"name": "Ty Fm.", "md_top": 1000.0, "md_base": 1050.0, "source": "test.csv"},
        {"name": "Heather Fm.", "md_top": 1050.0, "md_base": 1100.0, "source": "test.csv"},
    ]
    assert report["lithology"] == [
        {"md_top": 1000.0, "md_base": 1050.0, "lith": "sandstone"},
        {"md_top": 1050.0, "md_base": 1100.0, "lith": "shale"},
    ]


def test_build_formation_report_stats_have_evidence_ids_and_null_when_no_finite_samples() -> None:
    report = build_formation_report("W1", _table(), _tops(), EvidenceRegistry(), source="test.csv")
    ty_stats, heather_stats = report["stats"]
    assert ty_stats["avg_rop"]["value"] == 15.0
    assert ty_stats["avg_rop"]["evidence_id"].startswith("ev_")
    assert heather_stats["avg_rop"]["value"] is None  # all-NaN ROP in that interval
    assert heather_stats["avg_rop"]["evidence_id"].startswith("ev_")


def test_build_formation_report_confidence_reflects_sample_size() -> None:
    report = build_formation_report("W1", _table(), _tops(), EvidenceRegistry(), source="test.csv")
    for stat in report["stats"]:
        assert stat["confidence"]["level"] == "high"  # 50 samples each, >= 30 threshold (C2)


def test_build_formation_report_incidents_and_n_wells_are_honest_placeholders() -> None:
    report = build_formation_report("W1", _table(), _tops(), EvidenceRegistry(), source="test.csv")
    for stat in report["stats"]:
        assert stat["incidents"] == 0
        assert stat["n_wells"] == 1
        assert stat["best_window"] is None
