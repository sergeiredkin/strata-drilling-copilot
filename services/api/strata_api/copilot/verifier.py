"""Verifies a draft `CopilotAnswer`'s claims against evidence — docs/03_ARCHITECTURE.md §4.
Mutates nothing in place; returns a new, verified `CopilotAnswer`. Every number the answer or
reasoning text states must trace back to a claim with real evidence — this is the one place that
enforces that, independent of whatever the model itself said about its own confidence."""

from __future__ import annotations

import re

from strata_pipeline.contracts import Claim, CopilotAnswer
from strata_pipeline.evidence import EvidenceRegistry

from ..settings import Settings
from .tools import CopilotTools, ToolError

# Every Quantity in this codebase is written with precision=2 (docs/adr/0008); half the last
# displayed digit at that precision is the verifier's match tolerance (neither Claim nor Evidence
# carries its own precision field to derive this from more precisely — see the ADR).
_TOLERANCE = 0.005

# Same-physical-quantity unit groups the model might reasonably switch between even though every
# tool always returns one fixed unit — only time genuinely has this ambiguity in this schema's
# unit set (`m`, `kN`, `bar`, ... have no interchangeable sibling here).
_TIME_UNITS_TO_SECONDS = {"s": 1.0, "min": 60.0, "h": 3600.0}

_NUMBER_RE = re.compile(r"(?<![\w.])-?\d+\.?\d*(?![\w.])")


def _to_comparable(value: float, unit: str) -> tuple[float, str]:
    """Normalizes a value to a canonical (value, unit-group) pair so e.g. a claim in `min`
    verifies against evidence stored in `h`."""
    if unit in _TIME_UNITS_TO_SECONDS:
        return value * _TIME_UNITS_TO_SECONDS[unit], "time_s"
    return value, unit


def _verify_claim(claim: Claim, settings: Settings, reg: EvidenceRegistry) -> Claim:
    if claim.evidence_id is None:
        return claim.model_copy(update={"verified": False, "verify_note": "no evidence_id on this claim"})

    tools = CopilotTools(settings, reg)
    try:
        record = tools.evidence(claim.evidence_id)
    except ToolError:
        return claim.model_copy(
            update={"verified": False, "verify_note": f"unknown evidence id: {claim.evidence_id}"}
        )

    evidence_value = record.get("value")
    evidence_unit = record.get("unit")
    if evidence_value is None or evidence_unit is None:
        return claim.model_copy(update={"verified": False, "verify_note": "evidence has no value (null)"})

    claim_norm, claim_group = _to_comparable(claim.value, claim.unit.root)
    evidence_norm, evidence_group = _to_comparable(float(evidence_value), str(evidence_unit))
    if claim_group != evidence_group:
        return claim.model_copy(
            update={
                "verified": False,
                "verify_note": f"unit mismatch: claim is {claim.unit}, evidence is {evidence_unit}",
            }
        )
    if abs(claim_norm - evidence_norm) > _TOLERANCE * max(1.0, abs(evidence_norm)):
        note = f"value mismatch: claim={claim.value}{claim.unit}, evidence={evidence_value}{evidence_unit}"
        return claim.model_copy(update={"verified": False, "verify_note": note})
    return claim.model_copy(update={"verified": True, "verify_note": None})


def _unverified_numbers_in_text(answer: CopilotAnswer, verified_claims: list[Claim]) -> list[str]:
    """Numbers appearing in `answer`/`reasoning` prose that aren't covered by any verified
    claim — a model that writes a number without routing it through `submit_answer`'s `claims`
    list at all is exactly the failure this check exists to catch."""
    claimed_values = {round(c.value, 6) for c in verified_claims if c.verified}
    stray: list[str] = []
    for text in (answer.answer, answer.reasoning):
        for match in _NUMBER_RE.findall(text):
            try:
                value = round(float(match), 6)
            except ValueError:
                continue
            if value not in claimed_values:
                stray.append(match)
    return stray


def verify_answer(answer: CopilotAnswer, settings: Settings, reg: EvidenceRegistry) -> CopilotAnswer:
    verified_claims = [_verify_claim(c, settings, reg) for c in answer.claims]
    stray = _unverified_numbers_in_text(answer, verified_claims)
    return answer.model_copy(update={"claims": verified_claims, "unverified_numbers_in_text": stray or None})
