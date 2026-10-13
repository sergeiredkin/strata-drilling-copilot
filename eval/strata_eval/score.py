"""Scores `run_ablation.py`'s raw results into `EvalReport.ablation`'s `Metrics` shape and
writes them into `eval.json` — docs/02_IMPLEMENTATION_PLAN.md T9.2. Only touches the `ablation`
and `gold_set` fields; `qc` and `rigstate_agreement` are the export pipeline's own job and are
read back unchanged from whatever `eval.json` already has.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from strata_pipeline.contracts import EvalReport

from .run_ablation import ABLATION_CONFIGS, AblationConfig, ExpectedNumber, GoldSetMeta

# Same fixed display-rounding tolerance the live verifier uses when a gold question doesn't
# give its own (docs/adr/0008-copilot-tool-signatures.md decision 3).
_DEFAULT_TOLERANCE = 0.005


def _claims_of(result: dict[str, Any]) -> list[dict[str, Any]]:
    answer = result.get("answer")
    return answer["claims"] if answer else []


def _number_matches(expected: ExpectedNumber, claims: list[dict[str, Any]]) -> bool:
    for claim in claims:
        if not claim.get("verified"):
            continue
        if expected.evidence_id is not None:
            if claim["evidence_id"] == expected.evidence_id:
                return True
            continue
        if expected.unit is not None and claim["unit"] != expected.unit:
            continue
        tolerance = expected.tolerance if expected.tolerance is not None else _DEFAULT_TOLERANCE
        if expected.value is not None and abs(claim["value"] - expected.value) <= tolerance:
            return True
    return False


def _is_correct(result: dict[str, Any]) -> bool:
    answer = result.get("answer")
    if answer is None:
        return False
    if answer["kind"] != result["expected_kind"]:
        return False
    claims = _claims_of(result)
    return all(_number_matches(exp, claims) for exp in result["expected_numbers"])


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, float | None]:
    if not results:
        return {
            "answer_correctness": None,
            "numbers_verified_pct": None,
            "unsupported_numbers": None,
            "correct_insufficient_pct": None,
            "median_latency_s": None,
        }

    correctness = [1.0 if _is_correct(r) else 0.0 for r in results]
    all_claims = [c for r in results for c in _claims_of(r)]
    verified_pct = (
        100.0 * sum(1 for c in all_claims if c.get("verified")) / len(all_claims) if all_claims else None
    )
    unsupported_counts = [
        len((r["answer"] or {}).get("unverified_numbers_in_text") or []) for r in results if r.get("answer")
    ]
    insufficient_expected = [r for r in results if r["expected_kind"] == "insufficient_data"]
    correct_insufficient_pct = (
        100.0
        * sum(1 for r in insufficient_expected if r.get("answer") and r["answer"]["kind"] == "insufficient_data")
        / len(insufficient_expected)
        if insufficient_expected
        else None
    )
    latencies = [r["elapsed_s"] for r in results]

    return {
        "answer_correctness": sum(correctness) / len(correctness),
        "numbers_verified_pct": verified_pct,
        "unsupported_numbers": sum(unsupported_counts) / len(unsupported_counts) if unsupported_counts else None,
        "correct_insufficient_pct": correct_insufficient_pct,
        "median_latency_s": statistics.median(latencies) if latencies else None,
    }


def build_ablation_items(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_config: dict[AblationConfig, list[dict[str, Any]]] = {c: [] for c in ABLATION_CONFIGS}
    for r in results:
        by_config[r["config"]].append(r)
    return [{"config": config, "metrics": compute_metrics(rows)} for config, rows in by_config.items()]


def update_eval_json(eval_json_path: Path, gold_meta: GoldSetMeta, results: list[dict[str, Any]]) -> dict[str, Any]:
    existing = json.loads(eval_json_path.read_text(encoding="utf-8")) if eval_json_path.is_file() else {
        "qc": [], "rigstate_agreement": [],
    }
    updated = {
        **existing,
        "gold_set": {
            "n_questions": gold_meta.n_questions,
            "version": gold_meta.version,
            "author": gold_meta.author,
            "status": gold_meta.status,
        },
        "ablation": build_ablation_items(results),
    }
    EvalReport.model_validate(updated)  # fail loudly on a schema drift, not silently on write
    eval_json_path.write_text(json.dumps(updated, indent=2, sort_keys=True), encoding="utf-8")
    return updated
