from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RELIABILITY_MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)

VerificationStatus = Literal["passed", "failed", "inconclusive"]
ConfidenceBand = Literal["pass", "review", "block"]
AgentTraceStatus = Literal["running", "completed", "failed", "blocked", "needs_review"]
ToolCallStatus = Literal["succeeded", "failed", "blocked", "skipped"]


class VerificationCheckResult(BaseModel):
    check_name: str = Field(min_length=1, max_length=120)
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    detail: str = Field(min_length=1, max_length=1200)
    citation_ids: list[str] = Field(default_factory=list, max_length=50)

    model_config = RELIABILITY_MODEL_CONFIG


class VerificationOutcome(BaseModel):
    status: VerificationStatus
    score: float = Field(ge=0.0, le=1.0)
    checks: list[VerificationCheckResult] = Field(min_length=1, max_length=100)
    issues: list[str] = Field(default_factory=list, max_length=100)

    model_config = RELIABILITY_MODEL_CONFIG


class ConfidenceSignal(BaseModel):
    signal_name: str = Field(min_length=1, max_length=120)
    value: float = Field(ge=0.0, le=1.0)
    weight: float = Field(gt=0.0, le=1.0)
    detail: str | None = Field(default=None, max_length=1200)

    model_config = RELIABILITY_MODEL_CONFIG


class ConfidenceResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    band: ConfidenceBand
    signals: list[ConfidenceSignal] = Field(default_factory=list, max_length=50)
    verification_score: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = RELIABILITY_MODEL_CONFIG


class GateThresholds(BaseModel):
    pass_threshold: float = Field(ge=0.0, le=1.0)
    review_threshold: float = Field(ge=0.0, le=1.0)
    confidence_gating_enabled: bool

    model_config = RELIABILITY_MODEL_CONFIG


class GateDecision(BaseModel):
    decision: ConfidenceBand
    allow_execution: bool
    reason: str = Field(min_length=1, max_length=1200)
    thresholds: GateThresholds
    confidence_score: float = Field(ge=0.0, le=1.0)
    verification_status: VerificationStatus

    model_config = RELIABILITY_MODEL_CONFIG


class AgentToolCallTrace(BaseModel):
    sequence: int = Field(ge=1)
    tool_name: str = Field(min_length=1, max_length=120)
    status: ToolCallStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = Field(default=None, max_length=1200)

    model_config = RELIABILITY_MODEL_CONFIG


class AgentExecutionTrace(BaseModel):
    trace_id: str = Field(min_length=1, max_length=120)
    document_id: int = Field(ge=1)
    workflow_name: str = Field(min_length=1, max_length=120)
    status: AgentTraceStatus = "running"
    started_at: datetime
    completed_at: datetime | None = None
    tool_calls: list[AgentToolCallTrace] = Field(default_factory=list, max_length=500)
    verification: VerificationOutcome | None = None
    confidence: ConfidenceResult | None = None
    gate_decision: GateDecision | None = None

    model_config = RELIABILITY_MODEL_CONFIG


class ReliabilityAssessment(BaseModel):
    verification: VerificationOutcome
    confidence: ConfidenceResult
    gate_decision: GateDecision
    issues: list[str] = Field(default_factory=list, max_length=200)

    model_config = RELIABILITY_MODEL_CONFIG
