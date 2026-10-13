from __future__ import annotations

from pathlib import Path

from strata_eval.run_ablation import load_gold

GOLD_PATH = Path(__file__).resolve().parents[1] / "gold" / "questions.yaml"


def test_template_questions_yaml_is_pending_with_zero_real_questions() -> None:
    meta, questions = load_gold(GOLD_PATH)
    assert meta.status == "pending"
    assert meta.n_questions == 0  # the EXAMPLE- entry never counts
    assert any(q.id.startswith("EXAMPLE-") for q in questions)
