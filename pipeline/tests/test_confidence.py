from strata_pipeline.confidence import assess


def test_high_when_all_rules_high():
    c = assess(core_channel_coverage=0.95, sample_size=40, mean_rigstate_p=0.9)
    assert c["level"] == "high"


def test_level_is_lowest_across_applicable_rules():
    c = assess(core_channel_coverage=0.95, sample_size=5)  # C1 high, C2 low
    assert c["level"] == "low"
    assert c["rule_ids"] == ["C2"]


def test_zero_coverage_is_insufficient():
    c = assess(core_channel_coverage=0.0)
    assert c["level"] == "insufficient"


def test_no_inputs_is_insufficient():
    c = assess()
    assert c["level"] == "insufficient"
    assert c["rule_ids"] == []
