from strata_pipeline.evidence import EvidenceRegistry
from strata_pipeline.fixtures.formation import synthesize_formation_prediction, synthesize_formation_report
from strata_pipeline.fixtures.wells import WellSpec

VOLVE_SPEC = WellSpec(
    id="W_VOLVE", name="W Volve", field="Volve", years="2008-2016", md_range=(0.0, 4000.0),
    sections=["8½"], coverage_codes="pffpfn", qc_score=0.4, confidence_level="low",
    detailed=True, dense_days=2,
)
FORGE_SPEC = WellSpec(
    id="W_FORGE", name="W Forge", field="FORGE", years="2020-2022", md_range=(0.0, 3000.0),
    sections=["8¾"], coverage_codes="fffpff", qc_score=0.8, confidence_level="high",
    detailed=True, dense_days=2,
)


def test_synthesize_formation_report_covers_the_wells_full_md_range() -> None:
    report = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=1)
    tops = report["tops"]
    assert tops[0]["md_top"] == 0.0
    assert tops[-1]["md_base"] == 4000.0
    for a, b in zip(tops, tops[1:], strict=False):
        assert a["md_base"] == b["md_top"]


def test_synthesize_formation_report_uses_field_appropriate_lithology() -> None:
    volve = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=1)
    forge = synthesize_formation_report(FORGE_SPEC, EvidenceRegistry(), seed=1)
    assert any(lith["lith"] == "sandstone" for lith in volve["lithology"])
    assert {lith["lith"] for lith in forge["lithology"]} == {"other", "granite"}


def test_synthesize_formation_report_is_deterministic_for_a_given_seed() -> None:
    a = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=42)
    b = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=42)
    assert [s["avg_rop"]["value"] for s in a["stats"]] == [s["avg_rop"]["value"] for s in b["stats"]]


def test_synthesize_formation_prediction_covers_every_top_once() -> None:
    report = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=1)
    pred = synthesize_formation_prediction(VOLVE_SPEC, report, seed=1)
    assert len(pred["intervals"]) == len(report["tops"])
    assert pred["held_out"] is False


def test_synthesize_formation_prediction_has_at_least_one_abstain_or_disagreement() -> None:
    # Not a strict correctness check (it's fabricated demo data) -- just confirms the generator
    # doesn't always produce a perfect-looking, misleadingly-confident track.
    report = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=7)
    pred = synthesize_formation_prediction(VOLVE_SPEC, report, seed=7)
    assert any(iv["abstained"] or iv["agrees_with_pick"] is False for iv in pred["intervals"])


def test_synthesize_formation_prediction_abstained_intervals_have_no_label() -> None:
    report = synthesize_formation_report(VOLVE_SPEC, EvidenceRegistry(), seed=1)
    pred = synthesize_formation_prediction(VOLVE_SPEC, report, seed=1)
    for iv in pred["intervals"]:
        if iv["abstained"]:
            assert iv["label"] is None
            assert iv["agrees_with_pick"] is None
