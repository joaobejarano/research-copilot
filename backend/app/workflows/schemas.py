from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import MAX_WORKFLOW_CITATIONS, MAX_WORKFLOW_ITEMS

STRICT_MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)

WORKFLOW_STATUS_COMPLETED: Literal["completed"] = "completed"
WORKFLOW_STATUS_GENERATED: Literal["generated"] = "generated"
WORKFLOW_STATUS_INSUFFICIENT_EVIDENCE: Literal["insufficient_evidence"] = (
    "insufficient_evidence"
)


class WorkflowCitation(BaseModel):
    citation_id: str = Field(pattern=r"^C[1-9][0-9]*$")
    rank: int = Field(ge=1)
    document_id: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    page_number: int | None = None
    text_excerpt: str = Field(min_length=1, max_length=400)
    retrieval_score: float = Field(ge=-1.0, le=1.0)

    model_config = STRICT_MODEL_CONFIG


class WorkflowEvidence(BaseModel):
    citations: list[WorkflowCitation] = Field(
        default_factory=list,
        max_length=MAX_WORKFLOW_CITATIONS,
    )

    model_config = STRICT_MODEL_CONFIG


class CitationBackedItem(BaseModel):
    citation_ids: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)

    model_config = STRICT_MODEL_CONFIG


class BaseWorkflowRequest(BaseModel):
    document_id: int = Field(ge=1)
    instruction: str = Field(min_length=1, max_length=800)
    top_k: int | None = Field(default=None, ge=1)
    min_similarity: float | None = Field(default=None, ge=-1.0, le=1.0)

    model_config = STRICT_MODEL_CONFIG


class MemoCitationsBySection(BaseModel):
    company_overview: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)
    key_developments: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)
    risks: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)
    catalysts: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)
    kpis: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)
    open_questions: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_CITATIONS)

    model_config = STRICT_MODEL_CONFIG


class MemoDraft(BaseModel):
    company_overview: str = Field(min_length=1, max_length=2400)
    key_developments: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_ITEMS)
    risks: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_ITEMS)
    catalysts: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_ITEMS)
    kpis: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_ITEMS)
    open_questions: list[str] = Field(min_length=1, max_length=MAX_WORKFLOW_ITEMS)
    citations_by_section: MemoCitationsBySection

    model_config = STRICT_MODEL_CONFIG


class MemoGenerationRequest(BaseWorkflowRequest):
    workflow: Literal["memo_generation"] = "memo_generation"


class MemoGenerationOutput(BaseModel):
    workflow: Literal["memo_generation"] = "memo_generation"
    document_id: int = Field(ge=1)
    status: Literal["generated", "insufficient_evidence"]
    memo: MemoDraft | None = None
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)

    model_config = STRICT_MODEL_CONFIG


class KPIItem(CitationBackedItem):
    name: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=50)
    period: str | None = Field(default=None, max_length=120)
    direction: Literal["up", "down", "flat", "unknown"] = "unknown"
    commentary: str = Field(min_length=1, max_length=1200)


class KPIDraft(BaseModel):
    kpis: list[KPIItem] = Field(default_factory=list, max_length=MAX_WORKFLOW_ITEMS)

    model_config = STRICT_MODEL_CONFIG


class KPIExtractionRequest(BaseWorkflowRequest):
    workflow: Literal["kpi_extraction"] = "kpi_extraction"


class KPIExtractionOutput(BaseModel):
    workflow: Literal["kpi_extraction"] = "kpi_extraction"
    document_id: int = Field(ge=1)
    status: Literal["completed", "insufficient_evidence"]
    kpis: list[KPIItem] = Field(default_factory=list, max_length=MAX_WORKFLOW_ITEMS)
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)

    model_config = STRICT_MODEL_CONFIG


class RiskItem(CitationBackedItem):
    risk_title: str = Field(min_length=1, max_length=240)
    severity: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    horizon: Literal["short_term", "medium_term", "long_term", "unknown"] = "unknown"
    description: str = Field(min_length=1, max_length=1400)
    potential_impact: str = Field(min_length=1, max_length=1400)


class RiskDraft(BaseModel):
    risks: list[RiskItem] = Field(default_factory=list, max_length=MAX_WORKFLOW_ITEMS)

    model_config = STRICT_MODEL_CONFIG


class RiskExtractionRequest(BaseWorkflowRequest):
    workflow: Literal["risk_extraction"] = "risk_extraction"


class RiskExtractionOutput(BaseModel):
    workflow: Literal["risk_extraction"] = "risk_extraction"
    document_id: int = Field(ge=1)
    status: Literal["completed", "insufficient_evidence"]
    risks: list[RiskItem] = Field(default_factory=list, max_length=MAX_WORKFLOW_ITEMS)
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)

    model_config = STRICT_MODEL_CONFIG


class TimelineEvent(CitationBackedItem):
    date_label: str = Field(min_length=1, max_length=120)
    event_title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=1200)
    significance: str = Field(min_length=1, max_length=1200)


class TimelineDraft(BaseModel):
    events: list[TimelineEvent] = Field(default_factory=list, max_length=MAX_WORKFLOW_ITEMS)

    model_config = STRICT_MODEL_CONFIG


class TimelineBuildingRequest(BaseWorkflowRequest):
    workflow: Literal["timeline_building"] = "timeline_building"


class TimelineBuildingOutput(BaseModel):
    workflow: Literal["timeline_building"] = "timeline_building"
    document_id: int = Field(ge=1)
    status: Literal["completed", "insufficient_evidence"]
    events: list[TimelineEvent] = Field(default_factory=list, max_length=MAX_WORKFLOW_ITEMS)
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)

    model_config = STRICT_MODEL_CONFIG
