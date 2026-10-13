import numpy as np
from strata_pipeline.formation.classifier import (
    WellTrainingData,
    assemble_feature_matrix,
    lowo_evaluate,
    select_abstain_threshold,
)
from strata_pipeline.formation.depth_features import DepthFeatureTable


def _synthetic_table(n: int, seed: int, md_start: float = 1000.0) -> DepthFeatureTable:
    rng = np.random.default_rng(seed)
    md = np.arange(n, dtype="f8") + md_start
    return DepthFeatureTable(
        md=md,
        rop_m_per_h=rng.normal(15, 2, n),
        wob_kN=rng.normal(50, 5, n),
        rpm=rng.normal(120, 10, n),
        torque_kNm=rng.normal(20, 2, n),
        gas_pct=rng.normal(2, 0.5, n),
        mse_mpa=rng.normal(100, 10, n),
        dxc=rng.normal(1.2, 0.1, n),
        n_samples=np.full(n, 10.0),
    )


def _well_with_two_formations(well: str, seed: int) -> WellTrainingData:
    # First half "SAND", second half "SHALE" -- separable via a strong MSE offset so the
    # classifier has something real to learn, not noise.
    n = 60
    table = _synthetic_table(n, seed)
    table.mse_mpa[: n // 2] += 50.0  # SAND: distinctly higher MSE
    labels = np.array(["SAND"] * (n // 2) + ["SHALE"] * (n - n // 2), dtype=object)
    return WellTrainingData(well=well, table=table, labels=labels)


def test_assemble_feature_matrix_shape_matches_base_features_and_windows() -> None:
    table = _synthetic_table(50, seed=0)
    x, names = assemble_feature_matrix(table, rolling_windows_m=(5, 20))
    assert x.shape == (50, 7 * (1 + 2 * 2))
    assert len(names) == x.shape[1]
    assert "mse" in names
    assert "mse_mean5m" in names
    assert "mse_std20m" in names


def test_select_abstain_threshold_reaches_target_precision() -> None:
    # Half the predictions are correct with high confidence, half wrong with low confidence --
    # a threshold between the two confidence bands should isolate the correct, high-precision set.
    probs = np.array([0.9, 0.95, 0.92, 0.5, 0.55, 0.52])
    preds = np.array(["A", "A", "A", "B", "B", "B"])
    y_true = np.array(["A", "A", "A", "A", "A", "A"])  # low-confidence predictions are all wrong
    tau = select_abstain_threshold(probs, preds, y_true, target_precision=0.9)
    kept = probs >= tau
    assert np.mean(preds[kept] == y_true[kept]) >= 0.9


def test_select_abstain_threshold_returns_one_when_unreachable() -> None:
    probs = np.array([0.6, 0.6, 0.6])
    preds = np.array(["A", "A", "A"])
    y_true = np.array(["B", "B", "B"])  # always wrong -- no threshold reaches 0.9 precision
    assert select_abstain_threshold(probs, preds, y_true, target_precision=0.9) == 1.0


def test_lowo_evaluate_learns_a_separable_two_class_problem() -> None:
    wells = [_well_with_two_formations(f"W{i}", seed=i) for i in range(4)]
    result = lowo_evaluate(wells, target_precision=0.7)
    assert len(result.folds) == 4
    assert result.overall_accuracy > 0.6  # well above chance (0.5) on a separable problem
    assert 0.0 <= result.overall_abstain_rate <= 1.0
    assert 0.0 <= result.ece <= 1.0
    assert set(result.classes) == {"SAND", "SHALE"}


def test_lowo_evaluate_reports_one_fold_per_well() -> None:
    wells = [_well_with_two_formations(f"W{i}", seed=i) for i in range(3)]
    result = lowo_evaluate(wells)
    assert {f.well for f in result.folds} == {"W0", "W1", "W2"}
    assert all(f.n_labeled == 60 for f in result.folds)
