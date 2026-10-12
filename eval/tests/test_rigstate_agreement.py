from datetime import UTC, datetime, timedelta

from strata_eval.rigstate_agreement import (
    GoldWindow,
    compute_agreement,
    load_gold,
    majority_predicted_state,
)
from strata_pipeline.rigstate.intervals import RigStateInterval

T0 = datetime(2013, 1, 1, tzinfo=UTC)


def _iv(t0_offset_s: float, t1_offset_s: float, state: str) -> RigStateInterval:
    return RigStateInterval(
        t0=T0 + timedelta(seconds=t0_offset_s),
        t1=T0 + timedelta(seconds=t1_offset_s),
        state=state,
        rule_id="R4",
        confidence=1.0,
        back_reaming=False,
        n_samples=int(t1_offset_s - t0_offset_s) + 1,
    )


def test_majority_predicted_state_picks_most_overlap():
    intervals = [_iv(0, 300, "rotary_drilling"), _iv(301, 600, "circulating")]
    state = majority_predicted_state(intervals, T0, T0 + timedelta(seconds=600))
    assert state == "rotary_drilling"


def test_majority_predicted_state_none_when_no_overlap():
    intervals = [_iv(0, 300, "rotary_drilling")]
    state = majority_predicted_state(intervals, T0 + timedelta(seconds=1000), T0 + timedelta(seconds=1600))
    assert state is None


def test_compute_agreement_perfect_match():
    gold = [
        GoldWindow(well="W1", t0=T0, t1=T0 + timedelta(seconds=600), label="rotary_drilling"),
        GoldWindow(
            well="W1",
            t0=T0 + timedelta(seconds=600),
            t1=T0 + timedelta(seconds=1200),
            label="circulating",
        ),
    ]
    predicted = {
        "W1": [
            _iv(0, 600, "rotary_drilling"),
            _iv(600, 1200, "circulating"),
        ]
    }
    report = compute_agreement(gold, predicted)
    assert report.overall_agreement == 1.0
    assert report.n_compared == 2
    assert report.n_unlabelled_by_model == 0
    assert report.per_state["rotary_drilling"] == {"precision": 1.0, "recall": 1.0}
    assert report.per_well_agreement["W1"] == 1.0


def test_compute_agreement_tracks_misclassification_in_confusion_matrix():
    gold = [
        GoldWindow(well="W1", t0=T0, t1=T0 + timedelta(seconds=600), label="rotary_drilling"),
        GoldWindow(
            well="W1",
            t0=T0 + timedelta(seconds=600),
            t1=T0 + timedelta(seconds=1200),
            label="rotary_drilling",
        ),
    ]
    predicted = {"W1": [_iv(0, 600, "sliding"), _iv(600, 1200, "rotary_drilling")]}
    report = compute_agreement(gold, predicted)
    assert report.overall_agreement == 0.5
    # one rotary_drilling window was correctly caught, one true rotary_drilling was missed.
    assert report.per_state["rotary_drilling"]["recall"] == 0.5
    assert report.per_state["rotary_drilling"]["precision"] == 1.0


def test_compute_agreement_excludes_windows_with_no_model_coverage():
    gold = [GoldWindow(well="W1", t0=T0, t1=T0 + timedelta(seconds=600), label="rotary_drilling")]
    report = compute_agreement(gold, {"W1": []})
    assert report.n_unlabelled_by_model == 1
    assert report.n_compared == 0
    assert report.overall_agreement is None
    assert report.per_well_agreement["W1"] is None


def test_compute_agreement_unknown_well_has_no_coverage():
    gold = [GoldWindow(well="W_MISSING", t0=T0, t1=T0 + timedelta(seconds=600), label="rotary_drilling")]
    report = compute_agreement(gold, {"W1": [_iv(0, 600, "rotary_drilling")]})
    assert report.n_unlabelled_by_model == 1
    assert report.overall_agreement is None


def test_load_gold_parses_pending_header_only_file_as_empty(tmp_path):
    f = tmp_path / "rigstate_gold.csv"
    f.write_text("well,t0,t1,label,notes\n")
    assert load_gold(f) == []


def test_load_gold_parses_real_row(tmp_path):
    f = tmp_path / "rigstate_gold.csv"
    f.write_text(
        "well,t0,t1,label,notes\n"
        "15_9-F-11_A,2013-05-15T08:00:00+00:00,2013-05-15T08:10:00+00:00,rotary_drilling,clean\n"
    )
    rows = load_gold(f)
    assert len(rows) == 1
    assert rows[0].well == "15_9-F-11_A"
    assert rows[0].label == "rotary_drilling"
    assert rows[0].t1 - rows[0].t0 == timedelta(minutes=10)
    assert rows[0].notes == "clean"
