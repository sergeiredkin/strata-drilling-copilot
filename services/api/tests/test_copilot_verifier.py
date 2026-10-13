"""Unit tests for copilot/verifier.py — docs/02_IMPLEMENTATION_PLAN.md T8.4's acceptance
criterion: "verifier tests (match, unit mismatch, rounding, missing evidence, stray numbers in
text)"."""

from __future__ import annotations

from pathlib import Path

import pytest
from strata_api.copilot.verifier import verify_answer
from strata_api.settings import Settings
from strata_pipeline.contracts import Claim, CopilotAnswer
from strata_pipeline.evidence import EvidenceRegistry

FIXTURE_DATA_DIR = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "data"


@pytest.fixture
def settings() -> Settings:
    return Settings(data_dir=FIXTURE_DATA_DIR, cors_origins=[])


@pytest.fixture
def reg() -> EvidenceRegistry:
    return EvidenceRegistry(git_commit="test")


def _answer(claim: Claim, answer_text: str = "", reasoning: str = "") -> CopilotAnswer:
    return CopilotAnswer(
        kind="answer",
        answer=answer_text,
        claims=[claim],
        ddr_quotes=[],
        reasoning=reasoning,
        assumptions=[],
        confidence="high",
        confidence_reason="test",
        trace=[],
    )


def test_claim_matching_evidence_exactly_verifies(settings: Settings, reg: EvidenceRegistry) -> None:
    q = reg.quantity("test.tool", {"x": 1}, 6.15, "min", [], 2)
    claim = Claim(text="t", value=6.15, unit="min", evidence_id=q["evidence_id"], verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is True
    assert result.claims[0].verify_note is None


def test_claim_within_display_rounding_tolerance_verifies(settings: Settings, reg: EvidenceRegistry) -> None:
    q = reg.quantity("test.tool", {"x": 1}, 6.1500000001, "min", [], 2)
    claim = Claim(text="t", value=6.15, unit="min", evidence_id=q["evidence_id"], verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is True


def test_claim_with_unit_mismatch_fails_verification(settings: Settings, reg: EvidenceRegistry) -> None:
    q = reg.quantity("test.tool", {"x": 1}, 6.15, "min", [], 2)
    claim = Claim(text="t", value=6.15, unit="kN", evidence_id=q["evidence_id"], verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is False
    assert "unit mismatch" in result.claims[0].verify_note


def test_claim_in_equivalent_time_unit_still_verifies(settings: Settings, reg: EvidenceRegistry) -> None:
    # 1 h of evidence stated as 60 min in the claim — same physical quantity, different unit.
    q = reg.quantity("test.tool", {"x": 1}, 1.0, "h", [], 2)
    claim = Claim(text="t", value=60.0, unit="min", evidence_id=q["evidence_id"], verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is True


def test_claim_with_wrong_value_fails_verification(settings: Settings, reg: EvidenceRegistry) -> None:
    q = reg.quantity("test.tool", {"x": 1}, 6.15, "min", [], 2)
    claim = Claim(text="t", value=99.0, unit="min", evidence_id=q["evidence_id"], verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is False
    assert "value mismatch" in result.claims[0].verify_note


def test_claim_with_missing_evidence_id_fails_verification(settings: Settings, reg: EvidenceRegistry) -> None:
    claim = Claim(text="t", value=6.15, unit="min", evidence_id=None, verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is False
    assert "no evidence_id" in result.claims[0].verify_note


def test_claim_with_unknown_evidence_id_fails_verification(settings: Settings, reg: EvidenceRegistry) -> None:
    claim = Claim(text="t", value=6.15, unit="min", evidence_id="ev_0000000000", verified=False)
    result = verify_answer(_answer(claim), settings, reg)
    assert result.claims[0].verified is False
    assert "unknown evidence id" in result.claims[0].verify_note


def test_number_in_prose_not_backed_by_a_claim_is_flagged(settings: Settings, reg: EvidenceRegistry) -> None:
    q = reg.quantity("test.tool", {"x": 1}, 6.15, "min", [], 2)
    claim = Claim(text="t", value=6.15, unit="min", evidence_id=q["evidence_id"], verified=False)
    answer = _answer(claim, answer_text="Connection time was 6.15 min, roughly 3x the 2.1 min target.")
    result = verify_answer(answer, settings, reg)
    assert result.unverified_numbers_in_text is not None
    assert "2.1" in result.unverified_numbers_in_text


def test_every_number_in_prose_backed_by_claims_has_no_stray_numbers(
    settings: Settings, reg: EvidenceRegistry
) -> None:
    q = reg.quantity("test.tool", {"x": 1}, 6.15, "min", [], 2)
    claim = Claim(text="t", value=6.15, unit="min", evidence_id=q["evidence_id"], verified=False)
    answer = _answer(claim, answer_text="Connection time was 6.15 min.")
    result = verify_answer(answer, settings, reg)
    assert result.unverified_numbers_in_text is None
