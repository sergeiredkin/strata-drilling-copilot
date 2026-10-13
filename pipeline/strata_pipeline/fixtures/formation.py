"""Synthetic `formations.json`/`formation_pred.json` for the mock detailed wells (S6, T11.3) —
same "plausible but fabricated, clearly `is_mock`" contract every other fixture number in this
package already follows (`fixtures/synth.py`'s module docstring). Real wells never go through
here — `export/generate_real.py`'s `build_formation_report` (ground truth, not synthesized) is
the only path for those, and it overwrites whatever this module wrote for `15_9-F-11_A` once a
real export runs.

Per-field formation lists reuse the same North Sea Viking Graben names/lithology
`formation.report.FORMATION_LITHOLOGY` already has for the real Volve well, since F-5/F-1 C are
the same real field (just without real logs/tops used here) — a FORGE-appropriate two-layer
column (overburden + granitoid basement) covers the other field."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..confidence import assess
from ..evidence import EvidenceRegistry
from ..formation.report import lith_for_formation
from .wells import WellSpec

_VOLVE_FORMATIONS = [
    "Utsira Fm.", "Ty Fm.", "Ekofisk Fm.", "Hod Fm.", "Draupne Fm.", "Heather Fm.",
    "Hugin Fm. VOLVE", "Sleipner Fm.",
]
_FORGE_FORMATIONS = ["Overburden", "Granitoid basement"]

_FORGE_LITHOLOGY = {"Overburden": "other", "Granitoid basement": "granite"}

_ROP_RANGE_M_PER_H = (6.0, 24.0)
_MSE_RANGE_MPA = (40.0, 220.0)
_TAU = 0.75  # demo abstain threshold -- not fitted, just a plausible display value for mock data


def _formations_for_field(field: str) -> list[str]:
    return _FORGE_FORMATIONS if field == "FORGE" else _VOLVE_FORMATIONS


def _lith(field: str, name: str) -> str:
    return _FORGE_LITHOLOGY.get(name, "other") if field == "FORGE" else lith_for_formation(name)


def synthesize_formation_report(spec: WellSpec, reg: EvidenceRegistry, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    names = _formations_for_field(spec.field)
    md_lo, md_hi = spec.md_range
    # Evenly split the well's MD range across its formation list -- a mock stand-in for a real
    # top pick's irregular spacing, not a claim about true layer thickness.
    boundaries = np.linspace(md_lo, md_hi, len(names) + 1)

    tops_payload = []
    lithology_payload = []
    stats = []
    source = "fixture:synthetic"
    src = [{"file": source, "sha256": "n/a"}]
    for i, name in enumerate(names):
        top, base = float(boundaries[i]), float(boundaries[i + 1])
        lith = _lith(spec.field, name)
        tops_payload.append({"name": name, "md_top": top, "md_base": base, "source": source})
        lithology_payload.append({"md_top": top, "md_base": base, "lith": lith})

        n = int(rng.integers(20, 80))  # plausible sample size, feeds C2 confidence honestly
        avg_rop = reg.quantity(
            "formation.stats", {"well": spec.id, "formation": name, "stat": "avg_rop"},
            float(rng.uniform(*_ROP_RANGE_M_PER_H)), "m/h", src, 2,
        )
        avg_mse = reg.quantity(
            "formation.stats", {"well": spec.id, "formation": name, "stat": "avg_mse"},
            float(rng.uniform(*_MSE_RANGE_MPA)), "MPa", src, 2,
        )
        stats.append({
            "formation": name, "avg_rop": avg_rop, "avg_mse": avg_mse,
            "incidents": 0, "n_wells": 1, "best_window": None, "confidence": assess(sample_size=n),
        })

    return {"well": spec.id, "tops": tops_payload, "lithology": lithology_payload, "stats": stats}


def synthesize_formation_prediction(
    spec: WellSpec, formation_report: dict[str, Any], seed: int, model_version: str = "mock-0.0.0"
) -> dict[str, Any]:
    """One predicted interval per true top, agreeing most of the time, abstaining or
    disagreeing often enough that S6's comp (abstain/disagree patterns) has something to show —
    deliberately not a perfect-looking demo."""
    rng = np.random.default_rng(seed + 1)
    names = [top["name"] for top in formation_report["tops"]]
    intervals = []
    for top in formation_report["tops"]:
        p = float(rng.uniform(0.55, 0.98))
        abstained = p < _TAU
        if abstained:
            label = None
        elif rng.uniform() < 0.15:  # occasional disagreement, even above tau
            label = str(rng.choice([n for n in names if n != top["name"]])) if len(names) > 1 else top["name"]
        else:
            label = top["name"]
        intervals.append({
            "md_top": top["md_top"],
            "md_base": top["md_base"],
            "label": label,
            "p": round(p, 3),
            "abstained": abstained,
            "agrees_with_pick": None if label is None else (label == top["name"]),
        })
    return {"well": spec.id, "model_version": model_version, "held_out": False, "intervals": intervals}


def synthesize_depth_series(spec: WellSpec, formation_report: dict[str, Any], seed: int) -> dict[str, Any]:
    """Smooth, clearly-synthetic ROP/MSE/dxc/gas/MW/ECD curves at 1 m MD bins across the well's
    full range — same role as `export/generate_real.py`'s real `depth_series.json` for the real
    well, but these mock detailed wells' synthetic channels (`fixtures/synth.py`) never had ROP/
    GAS/MW_IN/ECD at all, so there's nothing to bin; these are fabricated directly instead,
    varying smoothly by formation like the S6 comp's own demo generator does."""
    rng = np.random.default_rng(seed + 2)
    md_lo, md_hi = spec.md_range
    md = np.arange(md_lo, md_hi, 1.0)
    tops = formation_report["tops"]

    def _formation_at(m: float) -> int:
        for i, top in enumerate(tops):
            if top["md_top"] <= m < top["md_base"]:
                return i
        return len(tops) - 1

    idx = np.array([_formation_at(m) for m in md])

    def _noise(scale: float) -> np.ndarray:
        return rng.normal(0, scale, len(md))

    rop = np.array([rng.uniform(*_ROP_RANGE_M_PER_H) for _ in tops])[idx] + _noise(1.5)
    mse = np.array([rng.uniform(*_MSE_RANGE_MPA) for _ in tops])[idx] + _noise(8.0)
    dxc = 0.9 + (md - md_lo) / (md_hi - md_lo) * 0.6 + _noise(0.03)  # mild compaction trend
    gas = np.clip(np.full(len(md), 1.5) + _noise(0.5), 0.1, None)
    mw = np.full(len(md), 1.25) + _noise(0.02)
    ecd = mw + 0.08 + _noise(0.01)  # ECD a bit above static MW, as it physically should be

    def _series(unit: str, values: np.ndarray) -> dict[str, Any]:
        return {"unit": unit, "values": [round(float(v), 3) for v in values]}

    return {
        "well": spec.id,
        "md": md.tolist(),
        "channels": {
            "ROP": _series("m/h", rop),
            "MSE": _series("MPa", mse),
            "DXC": _series("1", dxc),
            "GAS": _series("%", gas),
            "MW_IN": _series("sg", mw),
            "ECD": _series("sg", ecd),
        },
    }


__all__ = ["synthesize_depth_series", "synthesize_formation_prediction", "synthesize_formation_report"]
