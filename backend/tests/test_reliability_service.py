from datetime import datetime, timezone

import pytest

from app.reliability.schemas import ConfidenceSignal, VerificationCheckResult
from app.reliability.service import ReliabilityService


def _check(name: str, passed: bool, score: float, detail: str) -> VerificationCheckResult:
    return VerificationCheckResult(
        check_name=name,
        passed=passed,
        score=score,
        detail=detail,
        citation_ids=["C1"] if passed else [],
    )


def test_service_rejects_invalid_threshold_configuration() -> None:
    with pytest.raises(ValueError, match="review_threshold"):
        ReliabilityService(pass_threshold=0.4, review_threshold=0.5)

    with pytest.raises(ValueError, match="max_agent_tool_calls"):
        ReliabilityService(max_agent_tool_calls=0)


def test_summarize_verification_returns_inconclusive_for_mixed_checks() -> None:
    service = ReliabilityService()
    outcome = service.summarize_verification(
        checks=[
            _check("citation_presence", True, 1.0, "Citations are present."),
            _check("grounding_consistency", False, 0.2, "Claim mismatch detected."),
        ]
    )

    assert outcome.status == "inconclusive"
    assert outcome.score == pytest.approx(0.6)
    assert outcome.issues == ["Claim mismatch detected."]


def test_score_confidence_uses_signals_and_verification_score() -> None:
    service = ReliabilityService(pass_threshold=0.7, review_threshold=0.4)
    verification = service.summarize_verification(
        checks=[_check("citation_presence", True, 0.8, "Coverage is strong.")]
    )
    confidence = service.score_confidence(
        signals=[
            ConfidenceSignal(signal_name="citation_density", value=0.9, weight=0.7),
            ConfidenceSignal(signal_name="retrieval_strength", value=0.8, weight=0.3),
        ],
        verification=verification,
    )

    assert confidence.score == pytest.approx(0.835)
    assert confidence.band == "pass"
    assert confidence.verification_score == pytest.approx(0.8)


def test_score_confidence_uses_verification_score_when_signals_are_empty() -> None:
    service = ReliabilityService(pass_threshold=0.7, review_threshold=0.4)
    verification = service.summarize_verification(
        checks=[_check("citation_presence", True, 0.65, "Coverage is moderate.")]
    )

    confidence = service.score_confidence(signals=[], verification=verification)

    assert confidence.score == pytest.approx(0.65)
    assert confidence.band == "review"
    assert confidence.verification_score == pytest.approx(0.65)


def test_decide_gate_blocks_when_verification_failed() -> None:
    service = ReliabilityService(pass_threshold=0.7, review_threshold=0.4)
    verification = service.summarize_verification(
        checks=[_check("grounding_consistency", False, 0.1, "Unsupported claims found.")]
    )
    confidence = service.score_confidence(
        signals=[ConfidenceSignal(signal_name="retrieval_strength", value=0.9, weight=1.0)],
        verification=verification,
    )
    gate = service.decide_gate(confidence=confidence, verification=verification)

    assert gate.decision == "block"
    assert gate.allow_execution is False
    assert gate.reason == "Verification failed."


def test_decide_gate_returns_review_when_verification_is_inconclusive() -> None:
    service = ReliabilityService(pass_threshold=0.7, review_threshold=0.4)
    verification = service.summarize_verification(
        checks=[
            _check("citation_presence", True, 1.0, "Coverage is strong."),
            _check("grounding_consistency", False, 0.9, "One claim is weakly grounded."),
        ]
    )
    confidence = service.score_confidence(
        signals=[ConfidenceSignal(signal_name="retrieval_strength", value=1.0, weight=1.0)],
        verification=verification,
    )

    gate = service.decide_gate(confidence=confidence, verification=verification)

    assert confidence.band == "pass"
    assert gate.decision == "review"
    assert gate.allow_execution is False
    assert gate.reason == "Verification is inconclusive, manual review required."


def test_decide_gate_blocks_when_confidence_below_review_threshold() -> None:
    service = ReliabilityService(pass_threshold=0.8, review_threshold=0.6)
    verification = service.summarize_verification(
        checks=[_check("citation_presence", True, 1.0, "Citations are present.")]
    )
    confidence = service.score_confidence(
        signals=[ConfidenceSignal(signal_name="retrieval_strength", value=0.0, weight=1.0)],
        verification=verification,
    )

    gate = service.decide_gate(confidence=confidence, verification=verification)

    assert confidence.score == pytest.approx(0.5)
    assert confidence.band == "block"
    assert gate.decision == "block"
    assert gate.allow_execution is False
    assert gate.reason == "Confidence score below review threshold."


def test_decide_gate_passes_when_gating_disabled() -> None:
    service = ReliabilityService(enable_confidence_gating=False)
    verification = service.summarize_verification(
        checks=[_check("citation_presence", False, 0.1, "No citations.")]
    )
    confidence = service.score_confidence(
        signals=[ConfidenceSignal(signal_name="retrieval_strength", value=0.1, weight=1.0)],
        verification=verification,
    )
    gate = service.decide_gate(confidence=confidence, verification=verification)

    assert gate.decision == "pass"
    assert gate.allow_execution is True
    assert gate.reason == "Confidence gating disabled."


def test_execution_trace_enforces_max_tool_calls() -> None:
    service = ReliabilityService(max_agent_tool_calls=1)
    trace = service.start_trace(
        trace_id="trace-1",
        document_id=1,
        workflow_name="memo_generation",
        started_at=datetime(2026, 3, 22, tzinfo=timezone.utc),
    )
    trace = service.append_tool_call(
        trace=trace,
        tool_name="retrieve_relevant_chunks",
        status="succeeded",
        started_at=datetime(2026, 3, 22, 10, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 3, 22, 10, 0, 1, tzinfo=timezone.utc),
    )

    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].sequence == 1

    with pytest.raises(ValueError, match="max_agent_tool_calls"):
        service.append_tool_call(
            trace=trace,
            tool_name="verify_citations",
            status="succeeded",
        )


def test_finalize_trace_records_assessment_and_completion_timestamp() -> None:
    service = ReliabilityService()
    trace = service.start_trace(
        trace_id="trace-2",
        document_id=2,
        workflow_name="constrained_research_agent",
        started_at=datetime(2026, 3, 22, 11, 0, tzinfo=timezone.utc),
    )
    verification = service.summarize_verification(
        checks=[_check("citation_presence", True, 1.0, "All claims have citations.")]
    )
    confidence = service.score_confidence(
        signals=[ConfidenceSignal(signal_name="retrieval_strength", value=1.0, weight=1.0)],
        verification=verification,
    )
    gate = service.decide_gate(confidence=confidence, verification=verification)

    finalized = service.finalize_trace(
        trace=trace,
        status="completed",
        verification=verification,
        confidence=confidence,
        gate_decision=gate,
        completed_at=datetime(2026, 3, 22, 11, 0, 1, tzinfo=timezone.utc),
    )

    assert finalized.status == "completed"
    assert finalized.completed_at == datetime(2026, 3, 22, 11, 0, 1, tzinfo=timezone.utc)
    assert finalized.verification is not None
    assert finalized.confidence is not None
    assert finalized.gate_decision is not None
