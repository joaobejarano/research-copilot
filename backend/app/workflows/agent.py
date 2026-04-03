import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.qa.service import QuestionAnswerResult, answer_document_question
from app.reliability.schemas import (
    AgentExecutionTrace,
    AgentTraceStatus,
    ConfidenceResult,
    ConfidenceSignal,
    GateDecision,
    VerificationCheckResult,
    VerificationOutcome,
)
from app.reliability.service import ReliabilityService
from app.workflows.schemas import (
    KPIExtractionRequest,
    MemoGenerationRequest,
    RiskExtractionRequest,
    TimelineBuildingRequest,
)
from app.workflows.service import StructuredWorkflowService

AGENT_MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)

AgentToolName = Literal["ask", "memo", "extract_kpis", "extract_risks", "build_timeline"]
AgentRunStatus = Literal["passed", "needs_review", "blocked"]

TOOL_KEYWORD_PATTERN = re.compile(r"[a-z0-9]+")
QUESTION_PREFIXES = ("what ", "why ", "how ", "when ", "where ", "who ", "which ")

TOOL_ORDER: tuple[AgentToolName, ...] = (
    "memo",
    "extract_kpis",
    "extract_risks",
    "build_timeline",
    "ask",
)

SUPPORTED_TOOL_COUNT = len(TOOL_ORDER)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConstrainedResearchAgentOutput(BaseModel):
    document_id: int = Field(ge=1)
    instruction: str = Field(min_length=1, max_length=1200)
    status: AgentRunStatus
    selected_tools: list[AgentToolName] = Field(default_factory=list, max_length=SUPPORTED_TOOL_COUNT)
    trace: AgentExecutionTrace
    outputs: dict[str, Any] = Field(default_factory=dict)
    outputs_withheld: bool = False
    decision_reasons: list[str] = Field(default_factory=list, max_length=100)
    confidence: ConfidenceResult
    gate_decision: GateDecision

    model_config = AGENT_MODEL_CONFIG


class ConstrainedResearchAgent:
    def __init__(
        self,
        *,
        workflow_service_factory: Callable[[], StructuredWorkflowService] | None = None,
        reliability_service: ReliabilityService | None = None,
    ) -> None:
        self._workflow_service_factory = workflow_service_factory or StructuredWorkflowService
        self._reliability_service = reliability_service or ReliabilityService()

    def run(
        self,
        *,
        db: Session,
        document_id: int,
        instruction: str,
        document_ready: bool,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> ConstrainedResearchAgentOutput:
        normalized_instruction = instruction.strip()
        selected_tools = self.select_tools(instruction=normalized_instruction)

        trace = self._reliability_service.start_trace(
            trace_id=self._build_trace_id(document_id=document_id, instruction=normalized_instruction),
            document_id=document_id,
            workflow_name="constrained_research_agent",
        )

        raw_outputs: dict[str, Any] = {}
        execution_error: str | None = None

        if not document_ready:
            trace = self._reliability_service.append_tool_call(
                trace=trace,
                tool_name="document_ready_check",
                status="blocked",
                started_at=_utcnow(),
                completed_at=_utcnow(),
                error="Document must be processed and ready before agent execution.",
            )
            execution_error = "Document is not ready."
        else:
            workflow_service: StructuredWorkflowService | None = None
            for tool_name in selected_tools:
                started_at = _utcnow()
                try:
                    output, workflow_service = self._execute_tool(
                        db=db,
                        tool_name=tool_name,
                        workflow_service=workflow_service,
                        document_id=document_id,
                        instruction=normalized_instruction,
                        top_k=top_k,
                        min_similarity=min_similarity,
                    )
                    raw_outputs[tool_name] = output
                    trace = self._reliability_service.append_tool_call(
                        trace=trace,
                        tool_name=tool_name,
                        status="succeeded",
                        started_at=started_at,
                        completed_at=_utcnow(),
                    )
                except Exception as exc:  # pragma: no cover - defensive fallback
                    execution_error = f"{type(exc).__name__}: {exc}"
                    trace = self._reliability_service.append_tool_call(
                        trace=trace,
                        tool_name=tool_name,
                        status="failed",
                        started_at=started_at,
                        completed_at=_utcnow(),
                        error=execution_error,
                    )
                    break

        verification_checks = self._build_verification_checks(
            selected_tools=selected_tools,
            outputs=raw_outputs,
            execution_error=execution_error,
        )
        verification = self._reliability_service.summarize_verification(checks=verification_checks)
        confidence_signals = self._build_confidence_signals(
            selected_tools=selected_tools,
            outputs=raw_outputs,
        )
        confidence = self._reliability_service.score_confidence(
            signals=confidence_signals,
            verification=verification,
        )
        gate_decision = self._reliability_service.decide_gate(
            confidence=confidence,
            verification=verification,
        )
        response_status = self._response_status_from_gate_decision(gate_decision.decision)
        trace_status = self._trace_status_from_gate_decision(gate_decision.decision)
        safe_outputs, outputs_withheld = self._apply_output_gate(
            raw_outputs=raw_outputs,
            decision=gate_decision.decision,
        )
        decision_reasons = self._build_decision_reasons(
            gate_decision=gate_decision,
            verification=verification,
            outputs_withheld=outputs_withheld,
        )
        trace = self._reliability_service.finalize_trace(
            trace=trace,
            status=trace_status,
            verification=verification,
            confidence=confidence,
            gate_decision=gate_decision,
        )

        return ConstrainedResearchAgentOutput(
            document_id=document_id,
            instruction=normalized_instruction,
            status=response_status,
            selected_tools=selected_tools,
            trace=trace,
            outputs=safe_outputs,
            outputs_withheld=outputs_withheld,
            decision_reasons=decision_reasons,
            confidence=confidence,
            gate_decision=gate_decision,
        )

    def select_tools(self, *, instruction: str) -> list[AgentToolName]:
        normalized_instruction = instruction.strip().lower()
        tokens = set(TOOL_KEYWORD_PATTERN.findall(normalized_instruction))

        selected_tools: list[AgentToolName] = []
        if "memo" in tokens:
            selected_tools.append("memo")
        if {"kpi", "kpis", "metric", "metrics"} & tokens:
            selected_tools.append("extract_kpis")
        if {"risk", "risks", "downside", "headwind", "headwinds"} & tokens:
            selected_tools.append("extract_risks")
        if {"timeline", "timelines", "chronology", "milestone", "milestones"} & tokens:
            selected_tools.append("build_timeline")

        wants_question_answer = (
            "?" in instruction
            or normalized_instruction.startswith(QUESTION_PREFIXES)
            or "answer this" in normalized_instruction
            or normalized_instruction.startswith("ask ")
        )
        if wants_question_answer or not selected_tools:
            selected_tools.append("ask")

        return selected_tools

    def _execute_tool(
        self,
        *,
        db: Session,
        tool_name: AgentToolName,
        workflow_service: StructuredWorkflowService | None,
        document_id: int,
        instruction: str,
        top_k: int | None,
        min_similarity: float | None,
    ) -> tuple[dict[str, Any], StructuredWorkflowService | None]:
        if tool_name == "ask":
            ask_kwargs: dict[str, Any] = {}
            if top_k is not None:
                ask_kwargs["top_k"] = top_k
            if min_similarity is not None:
                ask_kwargs["min_similarity"] = min_similarity

            ask_output = answer_document_question(
                db=db,
                document_id=document_id,
                question=instruction,
                **ask_kwargs,
            )
            return self._serialize_ask_output(ask_output), workflow_service

        service = workflow_service
        if service is None:
            service = self._workflow_service_factory()

        if tool_name == "memo":
            result = service.generate_memo(
                db=db,
                request=MemoGenerationRequest(
                    document_id=document_id,
                    instruction=instruction,
                    top_k=top_k,
                    min_similarity=min_similarity,
                ),
            )
            return result.model_dump(mode="json"), service

        if tool_name == "extract_kpis":
            result = service.extract_kpis(
                db=db,
                request=KPIExtractionRequest(
                    document_id=document_id,
                    instruction=instruction,
                    top_k=top_k,
                    min_similarity=min_similarity,
                ),
            )
            return result.model_dump(mode="json"), service

        if tool_name == "extract_risks":
            result = service.extract_risks(
                db=db,
                request=RiskExtractionRequest(
                    document_id=document_id,
                    instruction=instruction,
                    top_k=top_k,
                    min_similarity=min_similarity,
                ),
            )
            return result.model_dump(mode="json"), service

        result = service.build_timeline(
            db=db,
            request=TimelineBuildingRequest(
                document_id=document_id,
                instruction=instruction,
                top_k=top_k,
                min_similarity=min_similarity,
            ),
        )
        return result.model_dump(mode="json"), service

    def _build_verification_checks(
        self,
        *,
        selected_tools: list[AgentToolName],
        outputs: dict[str, Any],
        execution_error: str | None,
    ) -> list[VerificationCheckResult]:
        total_tools = len(selected_tools)
        executed_tools = len(outputs)
        supported_outputs = self._count_supported_outputs(outputs=outputs)
        support_ratio = supported_outputs / total_tools if total_tools else 0.0
        execution_ratio = executed_tools / total_tools if total_tools else 0.0

        if execution_error is not None:
            return [
                VerificationCheckResult(
                    check_name="tool_execution",
                    passed=False,
                    score=execution_ratio,
                    detail=f"Agent execution failed: {execution_error}",
                ),
                VerificationCheckResult(
                    check_name="output_support",
                    passed=False,
                    score=support_ratio,
                    detail="No supported outputs available due to failed execution.",
                ),
            ]

        return [
            VerificationCheckResult(
                check_name="tool_execution",
                passed=executed_tools == total_tools,
                score=execution_ratio,
                detail=f"Executed {executed_tools} out of {total_tools} selected tools.",
            ),
            VerificationCheckResult(
                check_name="output_support",
                passed=support_ratio >= 0.5 and supported_outputs > 0,
                score=support_ratio,
                detail=f"{supported_outputs} out of {total_tools} outputs had grounded support.",
            ),
        ]

    def _build_confidence_signals(
        self,
        *,
        selected_tools: list[AgentToolName],
        outputs: dict[str, Any],
    ) -> list[ConfidenceSignal]:
        total_tools = len(selected_tools)
        executed_tools = len(outputs)
        supported_outputs = self._count_supported_outputs(outputs=outputs)

        execution_ratio = executed_tools / total_tools if total_tools else 0.0
        support_ratio = supported_outputs / total_tools if total_tools else 0.0
        call_budget_ratio = total_tools / SUPPORTED_TOOL_COUNT if SUPPORTED_TOOL_COUNT else 1.0
        efficiency_score = max(0.0, 1.0 - call_budget_ratio)

        return [
            ConfidenceSignal(
                signal_name="tool_execution_ratio",
                value=execution_ratio,
                weight=0.5,
                detail=f"{executed_tools}/{total_tools} selected tools executed.",
            ),
            ConfidenceSignal(
                signal_name="supported_output_ratio",
                value=support_ratio,
                weight=0.4,
                detail=f"{supported_outputs}/{total_tools} outputs had grounded support.",
            ),
            ConfidenceSignal(
                signal_name="tool_call_efficiency",
                value=efficiency_score,
                weight=0.1,
                detail=f"Selected {total_tools} out of {SUPPORTED_TOOL_COUNT} available tools.",
            ),
        ]

    def _count_supported_outputs(self, *, outputs: dict[str, Any]) -> int:
        supported_outputs = 0
        for tool_name, output in outputs.items():
            if tool_name == "ask":
                if output.get("status") == "answered" and bool(output.get("citations")):
                    supported_outputs += 1
                continue
            if tool_name == "memo":
                if (
                    output.get("status") == "generated"
                    and output.get("memo") is not None
                    and bool(output.get("evidence", {}).get("citations"))
                ):
                    supported_outputs += 1
                continue
            if tool_name == "extract_kpis":
                if (
                    output.get("status") == "completed"
                    and bool(output.get("kpis"))
                    and bool(output.get("evidence", {}).get("citations"))
                ):
                    supported_outputs += 1
                continue
            if tool_name == "extract_risks":
                if (
                    output.get("status") == "completed"
                    and bool(output.get("risks"))
                    and bool(output.get("evidence", {}).get("citations"))
                ):
                    supported_outputs += 1
                continue
            if tool_name == "build_timeline":
                if (
                    output.get("status") == "completed"
                    and bool(output.get("events"))
                    and bool(output.get("evidence", {}).get("citations"))
                ):
                    supported_outputs += 1

        return supported_outputs

    @staticmethod
    def _response_status_from_gate_decision(
        decision: Literal["pass", "review", "block"]
    ) -> AgentRunStatus:
        if decision == "pass":
            return "passed"
        if decision == "review":
            return "needs_review"
        return "blocked"

    @staticmethod
    def _trace_status_from_gate_decision(
        decision: Literal["pass", "review", "block"]
    ) -> AgentTraceStatus:
        if decision == "pass":
            return "completed"
        if decision == "review":
            return "needs_review"
        return "blocked"

    @staticmethod
    def _apply_output_gate(
        *,
        raw_outputs: dict[str, Any],
        decision: Literal["pass", "review", "block"],
    ) -> tuple[dict[str, Any], bool]:
        if decision == "pass":
            return raw_outputs, False
        return {}, True

    @staticmethod
    def _build_decision_reasons(
        *,
        gate_decision: GateDecision,
        verification: VerificationOutcome,
        outputs_withheld: bool,
    ) -> list[str]:
        if gate_decision.decision == "pass":
            return []

        reasons: list[str] = [gate_decision.reason]
        if outputs_withheld:
            reasons.append(
                "Final outputs were withheld because confidence gating did not pass."
            )
        for issue in verification.issues:
            if issue not in reasons:
                reasons.append(issue)
        for check in verification.checks:
            if check.passed:
                continue
            if check.detail not in reasons:
                reasons.append(check.detail)
        return reasons

    @staticmethod
    def _build_trace_id(*, document_id: int, instruction: str) -> str:
        deterministic_hash = uuid5(
            NAMESPACE_URL,
            f"document:{document_id}:instruction:{instruction.lower()}",
        ).hex[:24]
        return f"agent-{document_id}-{deterministic_hash}"

    @staticmethod
    def _serialize_ask_output(result: QuestionAnswerResult) -> dict[str, Any]:
        return {
            "question": result.question,
            "answer": result.answer,
            "status": result.status,
            "citations": [
                {
                    "citation_id": citation.citation_id,
                    "rank": citation.rank,
                    "document_id": citation.document_id,
                    "chunk_index": citation.chunk_index,
                    "page_number": citation.page_number,
                    "text_excerpt": citation.text_excerpt,
                    "retrieval_score": citation.retrieval_score,
                }
                for citation in result.citations
            ],
        }
