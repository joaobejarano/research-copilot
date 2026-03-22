from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.reliability.schemas import (
    AgentExecutionTrace,
    ConfidenceResult,
    GateDecision,
    GateThresholds,
    VerificationCheckResult,
    VerificationOutcome,
)


def test_verification_outcome_forbids_extra_fields() -> None:
    check = VerificationCheckResult(
        check_name="citation_coverage",
        passed=True,
        score=1.0,
        detail="All extracted claims had citations.",
        citation_ids=["C1"],
    )

    with pytest.raises(ValidationError):
        VerificationOutcome(
            status="passed",
            score=1.0,
            checks=[check],
            issues=[],
            unexpected_field="nope",
        )


def test_confidence_result_rejects_invalid_band() -> None:
    with pytest.raises(ValidationError):
        ConfidenceResult(
            score=0.8,
            band="unknown",  # type: ignore[arg-type]
            signals=[],
            verification_score=0.8,
        )


def test_gate_decision_requires_threshold_structure() -> None:
    with pytest.raises(ValidationError):
        GateDecision(
            decision="pass",
            allow_execution=True,
            reason="ok",
            thresholds={"pass_threshold": 0.8},
            confidence_score=0.9,
            verification_status="passed",
        )


def test_agent_execution_trace_validates_document_id() -> None:
    with pytest.raises(ValidationError):
        AgentExecutionTrace(
            trace_id="trace-1",
            document_id=0,
            workflow_name="memo_generation",
            started_at=datetime.now(timezone.utc),
        )


def test_gate_thresholds_accepts_valid_configuration() -> None:
    thresholds = GateThresholds(
        pass_threshold=0.75,
        review_threshold=0.5,
        confidence_gating_enabled=True,
    )

    assert thresholds.pass_threshold == 0.75
    assert thresholds.review_threshold == 0.5
