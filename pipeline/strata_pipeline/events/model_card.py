"""T12.5 events model card — docs/06_SCREENS.md S5's "Event retrieval (not a predictor)" card.

T12.1's rule lexicon is retrieval, not a trained classifier, so there's no macro-F1/ECE/
calibration to report the way `formation/report.py`'s formation card eventually will. What *can*
be reported honestly today is how many candidates exist and across how many wells — not a
precision/recall number, since that needs the manual-review CSV over a representative sample
that `tasks/BACKLOG.md`'s "Needs Sergei" list still asks for. This module does NOT self-certify
that number by having the same pipeline that extracted the candidates also grade them; a known
false-positive pattern (found during T12.1 development, not a formal review) is recorded as a
limitation instead, exactly as discovered, not smoothed into a confidence-inspiring metric.
"""

from __future__ import annotations

from typing import Any


def build_events_model_card(issues: list[dict[str, Any]]) -> dict[str, Any]:
    n_wells = len({i["well"] for i in issues})
    return {
        "model": "events",
        "version": "rule-lexicon-0.1",
        "inputs": ["DDR narrative text"],
        "validation": (
            "Rule lexicon (07 §10); manual-review precision pending — see tasks/BACKLOG.md's "
            "\"Needs Sergei\" list."
        ),
        "n_wells": n_wells,
        "n_samples": len(issues),
        "metrics": {},
        "baseline_metrics": {},
        "limitations": [
            "Not a predictive model: a keyword-retrieval pass over DDR narratives, tagged "
            'extraction:"rule" on every Issue it produces, not something trained or validated.',
            "Precision is not self-certified here: a bare keyword match (e.g. \"power loss\") "
            'can false-positive against a cluster it does not semantically belong to — observed '
            "during development on real data, not from a formal review.",
            "No manual-review CSV exists yet for a representative sample of candidates.",
            "The optional LLM extraction pass (07 §10) is not built; every Issue here is rule-only.",
        ],
    }


__all__ = ["build_events_model_card"]
