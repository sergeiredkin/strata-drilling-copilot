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


def test_c3_rigstate_confidence_thresholds():
    assert assess(mean_rigstate_p=0.9)["level"] == "high"
    assert assess(mean_rigstate_p=0.75)["level"] == "medium"
    assert assess(mean_rigstate_p=0.5)["level"] == "low"


def test_c4_ddr_coverage_thresholds():
    assert assess(ddr_coverage=0.95)["level"] == "high"
    assert assess(ddr_coverage=0.70)["level"] == "medium"
    assert assess(ddr_coverage=0.10)["level"] == "low"
    assert assess(ddr_coverage=0.0)["level"] == "insufficient"


def test_binding_rule_ids_list_every_rule_tied_for_lowest():
    c = assess(core_channel_coverage=0.95, mean_rigstate_p=0.5, ddr_coverage=0.5)  # C3, C4 both "low"
    assert c["level"] == "low"
    assert c["rule_ids"] == ["C3", "C4"]
    assert "mean rig-state classifier confidence" in c["reason"]
    assert "DDR coverage" in c["reason"]
