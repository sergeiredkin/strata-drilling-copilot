"""The 9-well fixture roster — matches `docs/design/comps/S1-Field.dc.html` exactly (names,
field, MD range, sections, coverage, qc_score, confidence) so S1 renders pixel-identical to the
comp. Coverage-kind order is the schema's: time_logs, depth_logs, daily_reports, formation_tops,
survey, mud."""

from __future__ import annotations

from dataclasses import dataclass

COVERAGE_KINDS = ["time_logs", "depth_logs", "daily_reports", "formation_tops", "survey", "mud"]


@dataclass(frozen=True)
class WellSpec:
    id: str
    name: str
    field: str  # "Volve" | "FORGE"
    years: str
    md_range: tuple[float, float]
    sections: list[str]
    coverage_codes: str  # 6 chars of f(ull)/p(artial)/n(one), COVERAGE_KINDS order
    qc_score: float
    confidence_level: str
    detailed: bool = False
    dense_days: int = 0  # 0 = no detail series (summary-only well)


# Coverage codes taken verbatim from the comp, with one deliberate deviation: F-5's time_logs
# is 'p' (partial — "missing time logs on some days") rather than the comp's 'n' (none), because
# T1.2 in 02_IMPLEMENTATION_PLAN.md specifically describes F-5 as having partial/sparse time-log
# coverage, which needs an actual (if gappy) detail series, not an absent one. Per CLAUDE.md §3,
# the spec wins over the pixel comp when they disagree — noted again in the T1.2 commit/summary.
WELLS: list[WellSpec] = [
    WellSpec(
        id="15_9-F-11_A",
        name="15/9-F-11 A",
        field="Volve",
        years="2008–2016",
        md_range=(0, 3750),
        sections=["26", "17½", "12¼", "8½"],
        coverage_codes="ffffff",
        qc_score=0.91,
        confidence_level="high",
        detailed=True,
        dense_days=4,
    ),
    WellSpec(
        id="15_9-F-15_D",
        name="15/9-F-15 D",
        field="Volve",
        years="2008–2016",
        md_range=(0, 4090),
        sections=["17½", "12¼", "8½"],
        coverage_codes="fffpff",
        qc_score=0.84,
        confidence_level="high",
    ),
    WellSpec(
        id="15_9-F-14",
        name="15/9-F-14",
        field="Volve",
        years="2008–2016",
        md_range=(0, 3730),
        sections=["26", "17½", "12¼", "8½"],
        coverage_codes="pfffpf",
        qc_score=0.72,
        confidence_level="medium",
    ),
    WellSpec(
        id="15_9-F-12",
        name="15/9-F-12",
        field="Volve",
        years="2008–2016",
        md_range=(0, 3520),
        sections=["17½", "12¼", "8½"],
        coverage_codes="pffpfp",
        qc_score=0.66,
        confidence_level="medium",
    ),
    WellSpec(
        id="15_9-F-5",
        name="15/9-F-5",
        field="Volve",
        years="2008–2016",
        md_range=(0, 3680),
        sections=["12¼", "8½"],
        coverage_codes="pffpfn",  # see deviation note above (was 'nffpfn' in the comp)
        qc_score=0.41,
        confidence_level="low",
        detailed=True,
        dense_days=2,
    ),
    WellSpec(
        id="15_9-F-1_C",
        name="15/9-F-1 C",
        field="Volve",
        years="2008–2016",
        md_range=(0, 3680),
        sections=["8½"],
        coverage_codes="nfpnpn",
        qc_score=0.33,
        confidence_level="low",
    ),
    WellSpec(
        id="16A_78-32",
        name="16A(78)-32",
        field="FORGE",
        years="2020–2022",
        md_range=(0, 3340),
        sections=["26", "17½", "12¼", "8¾"],
        coverage_codes="fffpff",
        qc_score=0.82,
        confidence_level="high",
        detailed=True,
        dense_days=2,
    ),
    WellSpec(
        id="16B_78-32",
        name="16B(78)-32",
        field="FORGE",
        years="2020–2022",
        md_range=(0, 3300),
        sections=["17½", "12¼", "8¾"],
        coverage_codes="pffnfp",
        qc_score=0.58,
        confidence_level="medium",
    ),
    WellSpec(
        id="58-32",
        name="58-32",
        field="FORGE",
        years="2020–2022",
        md_range=(0, 2290),
        sections=["17½", "12¼", "8¾"],
        coverage_codes="nfpfnp",
        qc_score=0.37,
        confidence_level="low",
    ),
]
