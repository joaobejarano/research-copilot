from datetime import datetime, timezone

from app.core.config import (
    CONFIDENCE_PASS_THRESHOLD,
    CONFIDENCE_REVIEW_THRESHOLD,
    ENABLE_CONFIDENCE_GATING,
    MAX_AGENT_TOOL_CALLS,
)
from app.reliability.schemas import (
    AgentExecutionTrace,
    AgentToolCallTrace,
    AgentTraceStatus,
    ConfidenceBand,
    ConfidenceResult,
    ConfidenceSignal,
    GateDecision,
    GateThresholds,
    ToolCallStatus,
    VerificationCheckResult,
    VerificationOutcome,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReliabilityService:
    def __init__(
        self,
        *,
        pass_threshold: float = CONFIDENCE_PASS_THRESHOLD,
        review_threshold: float = CONFIDENCE_REVIEW_THRESHOLD,
        enable_confidence_gating: bool = ENABLE_CONFIDENCE_GATING,
        max_agent_tool_calls: int = MAX_AGENT_TOOL_CALLS,
    ) -> None:
        if not (0.0 <= review_threshold <= 1.0):
            raise ValueError("review_threshold must be between 0 and 1.")
        if not (0.0 <= pass_threshold <= 1.0):
            raise ValueError("pass_threshold must be between 0 and 1.")
        if review_threshold > pass_threshold:
            raise ValueError("review_threshold must be less than or equal to pass_threshold.")
        if max_agent_tool_calls <= 0:
            raise ValueError("max_agent_tool_calls must be greater than 0.")

        self.pass_threshold = pass_threshold
        self.review_threshold = review_threshold
        self.enable_confidence_gating = enable_confidence_gating
        self.max_agent_tool_calls = max_agent_tool_calls

    def summarize_verification(
        self,
        *,
        checks: list[VerificationCheckResult],
    ) -> VerificationOutcome:
        if not checks:
            raise ValueError("checks must include at least one verification result.")

        average_score = sum(check.score for check in checks) / len(checks)
        if all(check.passed for check in checks):
            status = "passed"
        elif all(not check.passed for check in checks):
            status = "failed"
        else:
            status = "inconclusive"

        issues = [check.detail for check in checks if not check.passed]
        return VerificationOutcome(
            status=status,
            score=average_score,
            checks=checks,
            issues=issues,
        )

    def score_confidence(
        self,
        *,
        signals: list[ConfidenceSignal],
        verification: VerificationOutcome | None = None,
    ) -> ConfidenceResult:
        if signals:
            total_weight = sum(signal.weight for signal in signals)
            weighted_sum = sum(signal.value * signal.weight for signal in signals)
            base_score = weighted_sum / total_weight
        elif verification is not None:
            base_score = verification.score
        else:
            base_score = 0.0

        final_score = (
            (base_score + verification.score) / 2.0
            if verification is not None and signals
            else base_score
        )
        band = self._band_for_score(final_score)

        return ConfidenceResult(
            score=round(final_score, 6),
            band=band,
            signals=signals,
            verification_score=verification.score if verification is not None else None,
        )

    def decide_gate(
        self,
        *,
        confidence: ConfidenceResult,
        verification: VerificationOutcome,
    ) -> GateDecision:
        thresholds = self.get_thresholds()

        if not self.enable_confidence_gating:
            return GateDecision(
                decision="pass",
                allow_execution=True,
                reason="Confidence gating disabled.",
                thresholds=thresholds,
                confidence_score=confidence.score,
                verification_status=verification.status,
            )

        if verification.status == "failed":
            return GateDecision(
                decision="block",
                allow_execution=False,
                reason="Verification failed.",
                thresholds=thresholds,
                confidence_score=confidence.score,
                verification_status=verification.status,
            )

        decision = confidence.band
        reason = "Confidence score passed threshold."
        if decision == "review":
            reason = "Confidence score requires review."
        if decision == "block":
            reason = "Confidence score below review threshold."
        if verification.status == "inconclusive" and decision == "pass":
            decision = "review"
            reason = "Verification is inconclusive, manual review required."

        return GateDecision(
            decision=decision,
            allow_execution=decision == "pass",
            reason=reason,
            thresholds=thresholds,
            confidence_score=confidence.score,
            verification_status=verification.status,
        )

    def start_trace(
        self,
        *,
        trace_id: str,
        document_id: int,
        workflow_name: str,
        started_at: datetime | None = None,
    ) -> AgentExecutionTrace:
        return AgentExecutionTrace(
            trace_id=trace_id,
            document_id=document_id,
            workflow_name=workflow_name,
            started_at=started_at or _utcnow(),
        )

    def append_tool_call(
        self,
        *,
        trace: AgentExecutionTrace,
        tool_name: str,
        status: ToolCallStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
    ) -> AgentExecutionTrace:
        if len(trace.tool_calls) >= self.max_agent_tool_calls:
            raise ValueError("max_agent_tool_calls limit reached for this trace.")

        next_sequence = len(trace.tool_calls) + 1
        tool_call = AgentToolCallTrace(
            sequence=next_sequence,
            tool_name=tool_name,
            status=status,
            started_at=started_at or _utcnow(),
            completed_at=completed_at,
            error=error,
        )

        updated_status = trace.status
        if status == "failed":
            updated_status = "failed"
        if status == "blocked":
            updated_status = "blocked"

        return trace.model_copy(
            update={
                "status": updated_status,
                "tool_calls": [*trace.tool_calls, tool_call],
            }
        )

    def finalize_trace(
        self,
        *,
        trace: AgentExecutionTrace,
        status: AgentTraceStatus,
        verification: VerificationOutcome | None = None,
        confidence: ConfidenceResult | None = None,
        gate_decision: GateDecision | None = None,
        completed_at: datetime | None = None,
    ) -> AgentExecutionTrace:
        return trace.model_copy(
            update={
                "status": status,
                "completed_at": completed_at or _utcnow(),
                "verification": verification,
                "confidence": confidence,
                "gate_decision": gate_decision,
            }
        )

    def get_thresholds(self) -> GateThresholds:
        return GateThresholds(
            pass_threshold=self.pass_threshold,
            review_threshold=self.review_threshold,
            confidence_gating_enabled=self.enable_confidence_gating,
        )

    def _band_for_score(self, score: float) -> ConfidenceBand:
        if score >= self.pass_threshold:
            return "pass"
        if score >= self.review_threshold:
            return "review"
        return "block"
