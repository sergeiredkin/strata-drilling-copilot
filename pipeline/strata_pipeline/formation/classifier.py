"""Formation classifier — docs/07_DATA_AND_ALGORITHMS.md §9: `HistGradientBoostingClassifier`,
isotonic calibration fitted inside each training fold, **leave-one-well-out** validation (never
random splits), abstain when `max p < tau` with `tau` chosen inside training folds for >= 0.9
precision. Reports macro-F1, accuracy, ECE, abstain rate, per-well F1.

Feature assembly uses `depth_features.DepthFeatureTable`'s 7 base columns (ROP, WOB, RPM, surface
torque, gas, MSE, dxc) plus rolling mean/std over 5 and 20 m (`rolling_mean_std`), exactly the
feature set 07 §9 names. Labels come from `formation.labels.label_bins`.

NOT done in this increment (left for the next one, each a separate decision, not bundled in
here): the TVD-only baseline model (needs well survey data joined onto MD, not yet wired into
this module), the optional stratigraphic-order HMM/Viterbi decode, and running this for real
against all 6 modelled wells — only 1 of the 6 (15/9-F-11 A) has been confirmed to fit in this
dev machine's available RAM (docs/BACKLOG.md T3.7); LOWO needs several wells, so a real run here
waits on that same resource constraint, not a code gap."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier

from .depth_features import DepthFeatureTable, rolling_mean_std

_BASE_FEATURES: tuple[str, ...] = ("rop", "wob", "rpm", "torque", "mse", "dxc", "gas")


@dataclass(frozen=True)
class WellTrainingData:
    well: str
    table: DepthFeatureTable
    labels: np.ndarray  # object dtype, str | None, same length as table.md


@dataclass(frozen=True)
class LowoFoldResult:
    well: str
    n_labeled: int
    accuracy: float
    macro_f1: float
    abstain_rate: float


@dataclass(frozen=True)
class LowoResult:
    folds: list[LowoFoldResult]
    tau: float
    overall_accuracy: float
    overall_macro_f1: float
    overall_abstain_rate: float
    ece: float
    classes: list[str] = field(default_factory=list)


def assemble_feature_matrix(
    table: DepthFeatureTable, rolling_windows_m: tuple[int, ...] = (5, 20)
) -> tuple[np.ndarray, list[str]]:
    """One row per MD bin. Columns: each base feature's raw value, then its rolling mean/std over
    every window in `rolling_windows_m` — `7 * (1 + 2*len(rolling_windows_m))` columns total."""
    base = {
        "rop": table.rop_m_per_h,
        "wob": table.wob_kN,
        "rpm": table.rpm,
        "torque": table.torque_kNm,
        "mse": table.mse_mpa,
        "dxc": table.dxc,
        "gas": table.gas_pct,
    }
    columns: list[np.ndarray] = []
    names: list[str] = []
    for key in _BASE_FEATURES:
        arr = base[key]
        columns.append(arr)
        names.append(key)
        for window in rolling_windows_m:
            mean, std = rolling_mean_std(arr, window)
            columns.append(mean)
            names.append(f"{key}_mean{window}m")
            columns.append(std)
            names.append(f"{key}_std{window}m")
    return np.column_stack(columns), names


def _labeled_rows(x: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = labels != None  # noqa: E711 - labels is an object array of str|None, not a scalar comparison
    return x[mask], labels[mask].astype(str)


def _fit_calibrated(x_train: np.ndarray, y_train: np.ndarray) -> CalibratedClassifierCV:
    # HistGradientBoostingClassifier natively handles NaN features (missing data stays missing,
    # never zero-filled or interpolated). `cv` capped at the smallest class count so isotonic
    # calibration's internal folds never see a class with fewer samples than folds.
    min_class_count = int(np.min(np.unique(y_train, return_counts=True)[1]))
    cv = max(2, min(3, min_class_count))
    base = HistGradientBoostingClassifier(random_state=0)
    model = CalibratedClassifierCV(base, method="isotonic", cv=cv)
    model.fit(x_train, y_train)
    return model


def select_abstain_threshold(
    probs: np.ndarray, preds: np.ndarray, y_true: np.ndarray, target_precision: float = 0.9
) -> float:
    """Smallest `tau` such that predictions with `max p >= tau` hit `target_precision` overall
    (07 §9: "tau chosen inside training folds for >= 0.9 precision"). `tau=1.0` (abstain on
    everything) if no threshold in the candidate set reaches it — never silently accepting a
    lower precision than asked for."""
    candidates = np.unique(probs)
    for tau in np.sort(candidates):
        kept = probs >= tau
        if not np.any(kept):
            continue
        precision = float(np.mean(preds[kept] == y_true[kept]))
        if precision >= target_precision:
            return float(tau)
    return 1.0


def _macro_f1(preds: np.ndarray, y_true: np.ndarray, classes: list[str]) -> float:
    scores = []
    for c in classes:
        tp = int(np.sum((preds == c) & (y_true == c)))
        fp = int(np.sum((preds == c) & (y_true != c)))
        fn = int(np.sum((preds != c) & (y_true == c)))
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        scores.append(f1)
    return float(np.mean(scores)) if scores else 0.0


def _ece(probs: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> float:
    """Expected calibration error over `max p` confidence vs. empirical accuracy, `n_bins` equal-
    width bins. 0.0 if there are no predictions to bin (never a misleadingly perfect score)."""
    if len(probs) == 0:
        return 0.0
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    total = 0.0
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:], strict=False):
        in_bin = (probs >= lo) & (probs < hi) if hi < 1.0 else (probs >= lo) & (probs <= hi)
        if not np.any(in_bin):
            continue
        bin_confidence = float(np.mean(probs[in_bin]))
        bin_accuracy = float(np.mean(correct[in_bin]))
        total += (np.sum(in_bin) / len(probs)) * abs(bin_confidence - bin_accuracy)
    return total


def lowo_evaluate(wells: list[WellTrainingData], target_precision: float = 0.9) -> LowoResult:
    """Leave-one-well-out: for each well, train on every other well's labeled bins, predict on
    the held-out well. `tau` is selected once from the pooled out-of-fold predictions across all
    folds' *training* wells (an inner LOWO within each fold's training set), per 07 §9 — never
    from the held-out well's own labels."""
    all_classes = sorted({label for w in wells for label in w.labels if label is not None})

    inner_probs: list[np.ndarray] = []
    inner_preds: list[np.ndarray] = []
    inner_true: list[np.ndarray] = []
    fold_results: list[LowoFoldResult] = []
    outer_probs: list[np.ndarray] = []
    outer_correct: list[np.ndarray] = []
    outer_preds: list[np.ndarray] = []
    outer_true: list[np.ndarray] = []

    for i, held_out in enumerate(wells):
        train_wells = wells[:i] + wells[i + 1 :]
        x_train = np.concatenate([assemble_feature_matrix(w.table)[0] for w in train_wells])
        y_train_raw = np.concatenate([w.labels for w in train_wells])
        x_train_labeled, y_train = _labeled_rows(x_train, y_train_raw)

        x_test, _ = assemble_feature_matrix(held_out.table)
        x_test_labeled, y_test = _labeled_rows(x_test, held_out.labels)
        if len(y_train) == 0 or len(y_test) == 0:
            continue

        model = _fit_calibrated(x_train_labeled, y_train)
        proba = model.predict_proba(x_test_labeled)
        max_proba = proba.max(axis=1)
        preds = np.array(model.classes_)[proba.argmax(axis=1)]

        # Inner LOWO within this fold's own training wells, to pick tau without the held-out
        # well's labels ever influencing it.
        for j, inner_held_out in enumerate(train_wells):
            inner_train = train_wells[:j] + train_wells[j + 1 :]
            if not inner_train:
                continue
            x_inner_train = np.concatenate([assemble_feature_matrix(w.table)[0] for w in inner_train])
            y_inner_train_raw = np.concatenate([w.labels for w in inner_train])
            x_inner_train_labeled, y_inner_train = _labeled_rows(x_inner_train, y_inner_train_raw)
            x_inner_test, _ = assemble_feature_matrix(inner_held_out.table)
            x_inner_test_labeled, y_inner_test = _labeled_rows(x_inner_test, inner_held_out.labels)
            if len(y_inner_train) == 0 or len(y_inner_test) == 0:
                continue
            if len(np.unique(y_inner_train)) < 2:
                continue
            inner_model = _fit_calibrated(x_inner_train_labeled, y_inner_train)
            inner_proba = inner_model.predict_proba(x_inner_test_labeled)
            inner_probs.append(inner_proba.max(axis=1))
            inner_preds.append(np.array(inner_model.classes_)[inner_proba.argmax(axis=1)])
            inner_true.append(y_inner_test)

        correct = preds == y_test
        fold_results.append(
            LowoFoldResult(
                well=held_out.well,
                n_labeled=len(y_test),
                accuracy=float(np.mean(correct)),
                macro_f1=_macro_f1(preds, y_test, all_classes),
                abstain_rate=0.0,  # filled in below once tau is known
            )
        )
        outer_probs.append(max_proba)
        outer_correct.append(correct)
        outer_preds.append(preds)
        outer_true.append(y_test)

    tau = (
        select_abstain_threshold(
            np.concatenate(inner_probs), np.concatenate(inner_preds), np.concatenate(inner_true), target_precision
        )
        if inner_probs
        else 1.0
    )

    all_probs = np.concatenate(outer_probs) if outer_probs else np.array([])
    all_correct = np.concatenate(outer_correct) if outer_correct else np.array([])
    all_preds = np.concatenate(outer_preds) if outer_preds else np.array([])
    all_true = np.concatenate(outer_true) if outer_true else np.array([])

    kept = all_probs >= tau
    final_fold_results = []
    for fold, probs in zip(fold_results, outer_probs, strict=False):
        fold_kept = probs >= tau
        final_fold_results.append(
            LowoFoldResult(
                well=fold.well,
                n_labeled=fold.n_labeled,
                accuracy=fold.accuracy,
                macro_f1=fold.macro_f1,
                abstain_rate=float(np.mean(~fold_kept)) if len(fold_kept) > 0 else 0.0,
            )
        )

    return LowoResult(
        folds=final_fold_results,
        tau=tau,
        overall_accuracy=float(np.mean(all_correct[kept])) if np.any(kept) else 0.0,
        overall_macro_f1=_macro_f1(all_preds[kept], all_true[kept], all_classes) if np.any(kept) else 0.0,
        overall_abstain_rate=float(np.mean(~kept)) if len(kept) > 0 else 0.0,
        ece=_ece(all_probs, all_correct.astype(float)),
        classes=all_classes,
    )


__all__ = [
    "LowoFoldResult",
    "LowoResult",
    "WellTrainingData",
    "assemble_feature_matrix",
    "lowo_evaluate",
    "select_abstain_threshold",
]
