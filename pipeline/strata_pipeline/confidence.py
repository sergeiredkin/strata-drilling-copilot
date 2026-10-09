"""Confidence rules — the ONLY implementation.

See `03_ARCHITECTURE.md` §5 and `07_DATA_AND_ALGORITHMS.md` §8. The front end renders
`{level, reason}`; it never computes confidence.
"""

from __future__ import annotations

Level = str  # "high" | "medium" | "low" | "insufficient"
_LEVEL_RANK: dict[Level, int] = {"insufficient": 0, "low": 1, "medium": 2, "high": 3}
_RANK_LEVEL = {v: k for k, v in _LEVEL_RANK.items()}


def _rule_c1_coverage(coverage_frac: float) -> Level:
    if coverage_frac >= 0.90:
        return "high"
    if coverage_frac >= 0.60:
        return "medium"
    if coverage_frac > 0:
        return "low"
    return "insufficient"


def _rule_c2_sample_size(n: int) -> Level:
    if n >= 30:
        return "high"
    if n >= 10:
        return "medium"
    if n >= 1:
        return "low"
    return "insufficient"


def _rule_c3_rigstate_p(mean_p: float) -> Level:
    if mean_p >= 0.85:
        return "high"
    if mean_p >= 0.70:
        return "medium"
    return "low"


def _rule_c4_ddr_coverage(ddr_coverage_frac: float) -> Level:
    if ddr_coverage_frac >= 0.90:
        return "high"
    if ddr_coverage_frac >= 0.60:
        return "medium"
    if ddr_coverage_frac > 0:
        return "low"
    return "insufficient"


def assess(
    *,
    core_channel_coverage: float | None = None,
    sample_size: int | None = None,
    mean_rigstate_p: float | None = None,
    ddr_coverage: float | None = None,
) -> dict[str, object]:
    """Applies rules C1-C4 (only the ones for which an input was given) and returns
    `{level, reason, rule_ids}` — level is the lowest across applicable rules."""
    levels: dict[str, Level] = {}
    if core_channel_coverage is not None:
        levels["C1"] = _rule_c1_coverage(core_channel_coverage)
    if sample_size is not None:
        levels["C2"] = _rule_c2_sample_size(sample_size)
    if mean_rigstate_p is not None:
        levels["C3"] = _rule_c3_rigstate_p(mean_rigstate_p)
    if ddr_coverage is not None:
        levels["C4"] = _rule_c4_ddr_coverage(ddr_coverage)

    if not levels:
        return {
            "level": "insufficient",
            "reason": "No applicable confidence rule had an input.",
            "rule_ids": [],
        }

    worst_rank = min(_LEVEL_RANK[lvl] for lvl in levels.values())
    level = _RANK_LEVEL[worst_rank]
    binding = sorted(rid for rid, lvl in levels.items() if _LEVEL_RANK[lvl] == worst_rank)

    reasons = {
        "C1": f"core-channel coverage in window is {core_channel_coverage:.0%}"
        if core_channel_coverage is not None
        else "",
        "C2": f"sample size is {sample_size}" if sample_size is not None else "",
        "C3": f"mean rig-state classifier confidence is {mean_rigstate_p:.2f}"
        if mean_rigstate_p is not None
        else "",
        "C4": f"DDR coverage is {ddr_coverage:.0%}" if ddr_coverage is not None else "",
    }
    reason = "; ".join(reasons[r] for r in binding if reasons[r])
    fallback = f"binding rule(s): {', '.join(binding)}"
    return {"level": level, "reason": reason or fallback, "rule_ids": binding}
