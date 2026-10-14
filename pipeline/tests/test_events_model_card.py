from strata_pipeline.events.model_card import build_events_model_card


def test_build_events_model_card_counts_wells_and_samples() -> None:
    issues = [
        {"well": "W1", "type": "tight_hole"},
        {"well": "W1", "type": "losses"},
        {"well": "W2", "type": "kick"},
    ]
    card = build_events_model_card(issues)
    assert card["model"] == "events"
    assert card["n_wells"] == 2
    assert card["n_samples"] == 3


def test_build_events_model_card_reports_no_precision_metric() -> None:
    card = build_events_model_card([{"well": "W1", "type": "tight_hole"}])
    assert card["metrics"] == {}


def test_build_events_model_card_notes_the_known_false_positive_pattern() -> None:
    card = build_events_model_card([])
    assert any("power loss" in limitation for limitation in card["limitations"])


def test_build_events_model_card_handles_zero_issues() -> None:
    card = build_events_model_card([])
    assert card["n_wells"] == 0
    assert card["n_samples"] == 0
