from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config import MCPServerSettings
from mcp_server.tools.documents import _request_backend_json

MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkflowCitation(BaseModel):
    citation_id: str = Field(pattern=r"^C[1-9][0-9]*$")
    rank: int = Field(ge=1)
    document_id: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    text_excerpt: str = Field(min_length=1, max_length=400)
    retrieval_score: float = Field(ge=-1.0, le=1.0)

    model_config = MODEL_CONFIG


class AskDocumentToolOutput(BaseModel):
    tool: Literal["ask_document"] = "ask_document"
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    status: Literal["answered", "insufficient_evidence"]
    citations: list[WorkflowCitation] = Field(default_factory=list, max_length=100)

    model_config = MODEL_CONFIG


class _BackendAskResponse(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    status: Literal["answered", "insufficient_evidence"]
    citations: list[WorkflowCitation] = Field(default_factory=list, max_length=100)

    model_config = MODEL_CONFIG


class MemoCitationsBySection(BaseModel):
    company_overview: list[str] = Field(default_factory=list)
    key_developments: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    model_config = MODEL_CONFIG


class MemoDraft(BaseModel):
    company_overview: str = Field(min_length=1, max_length=2400)
    key_developments: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    citations_by_section: MemoCitationsBySection

    model_config = MODEL_CONFIG


class GenerateMemoToolOutput(BaseModel):
    tool: Literal["generate_memo"] = "generate_memo"
    document_id: int = Field(ge=1)
    status: Literal["generated", "insufficient_evidence"]
    memo: MemoDraft | None = None

    model_config = MODEL_CONFIG


class _BackendMemoResponse(BaseModel):
    document_id: int = Field(ge=1)
    status: Literal["generated", "insufficient_evidence"]
    memo: MemoDraft | None = None

    model_config = MODEL_CONFIG


class RiskItem(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=1400)
    severity_or_materiality: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    citation: str = Field(pattern=r"^C[1-9][0-9]*$")

    model_config = MODEL_CONFIG


class WorkflowEvidence(BaseModel):
    citations: list[WorkflowCitation] = Field(default_factory=list, max_length=100)

    model_config = MODEL_CONFIG


class ExtractRisksToolOutput(BaseModel):
    tool: Literal["extract_risks"] = "extract_risks"
    workflow: Literal["risk_extraction"]
    document_id: int = Field(ge=1)
    status: Literal["completed", "insufficient_evidence"]
    risks: list[RiskItem] = Field(default_factory=list, max_length=100)
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)

    model_config = MODEL_CONFIG


class _BackendExtractRisksResponse(BaseModel):
    workflow: Literal["risk_extraction"]
    document_id: int = Field(ge=1)
    status: Literal["completed", "insufficient_evidence"]
    risks: list[RiskItem] = Field(default_factory=list, max_length=100)
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)

    model_config = MODEL_CONFIG


def _normalize_question(question: str) -> str:
    normalized = " ".join(question.split())
    if not normalized:
        raise ValueError("question must not be empty.")
    return normalized


def ask_document_from_backend(
    *,
    settings: MCPServerSettings,
    document_id: int,
    question: str,
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> AskDocumentToolOutput:
    if document_id < 1:
        raise ValueError("document_id must be >= 1.")

    body: dict[str, Any] = {
        "question": _normalize_question(question),
    }
    if top_k is not None:
        body["top_k"] = top_k
    if min_similarity is not None:
        body["min_similarity"] = min_similarity

    payload = _request_backend_json(
        base_url=settings.backend_base_url,
        path=f"/documents/{document_id}/ask",
        method="POST",
        body=body,
    )
    if not isinstance(payload, dict):
        raise ValueError("Backend /documents/{document_id}/ask response must be a JSON object.")

    ask_response = _BackendAskResponse.model_validate(payload)
    return AskDocumentToolOutput(
        question=ask_response.question,
        answer=ask_response.answer,
        status=ask_response.status,
        citations=ask_response.citations,
    )


def generate_memo_from_backend(
    *,
    settings: MCPServerSettings,
    document_id: int,
) -> GenerateMemoToolOutput:
    if document_id < 1:
        raise ValueError("document_id must be >= 1.")

    payload = _request_backend_json(
        base_url=settings.backend_base_url,
        path=f"/documents/{document_id}/memo",
        method="POST",
    )
    if not isinstance(payload, dict):
        raise ValueError("Backend /documents/{document_id}/memo response must be a JSON object.")

    memo_response = _BackendMemoResponse.model_validate(payload)
    return GenerateMemoToolOutput(
        document_id=memo_response.document_id,
        status=memo_response.status,
        memo=memo_response.memo,
    )


def extract_risks_from_backend(
    *,
    settings: MCPServerSettings,
    document_id: int,
) -> ExtractRisksToolOutput:
    if document_id < 1:
        raise ValueError("document_id must be >= 1.")

    payload = _request_backend_json(
        base_url=settings.backend_base_url,
        path=f"/documents/{document_id}/extract/risks",
        method="POST",
    )
    if not isinstance(payload, dict):
        raise ValueError(
            "Backend /documents/{document_id}/extract/risks response must be a JSON object."
        )

    risks_response = _BackendExtractRisksResponse.model_validate(payload)
    return ExtractRisksToolOutput(
        workflow=risks_response.workflow,
        document_id=risks_response.document_id,
        status=risks_response.status,
        risks=risks_response.risks,
        evidence=risks_response.evidence,
    )


def register_workflow_tools(*, server: FastMCP, settings: MCPServerSettings) -> None:
    @server.tool(
        name="ask_document",
        description=(
            "Run grounded Q&A for one document using the existing backend ask workflow. "
            "Returns answer, status, and citations."
        ),
        structured_output=True,
    )
    def ask_document(
        document_id: int,
        question: str,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> AskDocumentToolOutput:
        return ask_document_from_backend(
            settings=settings,
            document_id=document_id,
            question=question,
            top_k=top_k,
            min_similarity=min_similarity,
        )

    @server.tool(
        name="generate_memo",
        description=(
            "Generate a grounded memo for one document using the existing backend memo workflow. "
            "Preserves generated/insufficient_evidence statuses."
        ),
        structured_output=True,
    )
    def generate_memo(document_id: int) -> GenerateMemoToolOutput:
        return generate_memo_from_backend(settings=settings, document_id=document_id)

    @server.tool(
        name="extract_risks",
        description=(
            "Extract structured risks for one document using the existing backend risk workflow. "
            "Preserves completed/insufficient_evidence statuses."
        ),
        structured_output=True,
    )
    def extract_risks(document_id: int) -> ExtractRisksToolOutput:
        return extract_risks_from_backend(settings=settings, document_id=document_id)
