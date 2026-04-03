import asyncio

import httpx
import pytest

from app.api.routes import documents as documents_routes
from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.main import app
from app.qa.service import QuestionAnswerResult
from app.retrieval import service as retrieval_service
from app.workflows import agent as agent_workflow
from app.workflows.schemas import (
    KPIExtractionOutput,
    KPIItem,
    RiskExtractionOutput,
    RiskItem,
    WorkflowCitation,
    WorkflowEvidence,
)


class FakeEmbeddingProvider:
    def __init__(self, query_embedding: list[float]) -> None:
        self.query_embedding = query_embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.query_embedding for _ in texts]


class FakeStructuredWorkflowService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_memo(self, **kwargs):  # pragma: no cover - should not be called in this test.
        raise AssertionError("generate_memo should not be called.")

    def extract_kpis(self, **kwargs) -> KPIExtractionOutput:
        request = kwargs["request"]
        self.calls.append("extract_kpis")
        return KPIExtractionOutput(
            document_id=request.document_id,
            status="completed",
            kpis=[
                KPIItem(
                    name="Revenue",
                    value="120M",
                    unit="USD",
                    period="2024-Q4",
                    citation="C1",
                )
            ],
            evidence=WorkflowEvidence(
                citations=[
                    WorkflowCitation(
                        citation_id="C1",
                        rank=1,
                        document_id=request.document_id,
                        chunk_index=0,
                        page_number=1,
                        text_excerpt="Revenue increased to 120M in Q4.",
                        retrieval_score=0.9,
                    )
                ]
            ),
        )

    def extract_risks(self, **kwargs) -> RiskExtractionOutput:
        request = kwargs["request"]
        self.calls.append("extract_risks")
        return RiskExtractionOutput(
            document_id=request.document_id,
            status="completed",
            risks=[
                RiskItem(
                    title="FX volatility",
                    description="Currency swings can pressure margins.",
                    severity_or_materiality="medium",
                    citation="C1",
                )
            ],
            evidence=WorkflowEvidence(
                citations=[
                    WorkflowCitation(
                        citation_id="C1",
                        rank=1,
                        document_id=request.document_id,
                        chunk_index=1,
                        page_number=1,
                        text_excerpt="FX volatility remains elevated.",
                        retrieval_score=0.88,
                    )
                ]
            ),
        )

    def build_timeline(self, **kwargs):  # pragma: no cover - should not be called in this test.
        raise AssertionError("build_timeline should not be called.")


def _make_embedding(first: float, second: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = first
    vector[1] = second
    return vector


def _seed_document(status: str) -> int:
    db = SessionLocal()
    try:
        document = Document(
            company_name="Acme Corp",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="Acme_Corp/financial_report/2024-Q4/1.txt",
            status=status,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document.id
    finally:
        db.close()


def _seed_document_with_chunk(*, text: str) -> int:
    db = SessionLocal()
    try:
        document = Document(
            company_name="Acme Corp",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="Acme_Corp/financial_report/2024-Q4/1.txt",
            status="ready",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            page_number=1,
            text=text,
            token_count=20,
            embedding=_make_embedding(1.0, 0.0),
        )
        db.add(chunk)
        db.commit()
        return document.id
    finally:
        db.close()


def _agent(document_id: int, payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(f"/documents/{document_id}/agent", json=payload)

    return asyncio.run(request())


def _assert_trace_structure(
    *,
    trace: dict[str, object],
    expected_status: str,
    expected_document_id: int,
    expected_tool_name: str,
    expected_tool_status: str,
) -> None:
    assert trace["workflow_name"] == "constrained_research_agent"
    assert str(trace["trace_id"]).startswith(f"agent-{expected_document_id}-")
    assert trace["document_id"] == expected_document_id
    assert trace["status"] == expected_status
    assert trace["started_at"] is not None
    assert trace["completed_at"] is not None
    assert trace["verification"] is not None
    assert trace["confidence"] is not None
    assert trace["gate_decision"] is not None

    tool_calls = trace["tool_calls"]
    assert isinstance(tool_calls, list)
    assert len(tool_calls) == 1
    tool_call = tool_calls[0]
    assert tool_call["sequence"] == 1
    assert tool_call["tool_name"] == expected_tool_name
    assert tool_call["status"] == expected_tool_status
    assert tool_call["started_at"] is not None
    assert tool_call["completed_at"] is not None


def test_agent_endpoint_returns_passed_for_grounded_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document_with_chunk(
        text=(
            "Revenue increased 12 percent in Q4 due to subscription expansion "
            "and improved enterprise renewals."
        )
    )
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _agent(document_id, {"instruction": "What happened to revenue in Q4?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["instruction"] == "What happened to revenue in Q4?"
    assert payload["status"] == "passed"
    assert payload["selected_tools"] == ["ask"]
    assert payload["outputs_withheld"] is False
    assert payload["decision_reasons"] == []
    assert payload["outputs"]["ask"]["status"] == "answered"
    _assert_trace_structure(
        trace=payload["trace"],
        expected_status="completed",
        expected_document_id=document_id,
        expected_tool_name="ask",
        expected_tool_status="succeeded",
    )
    assert payload["confidence"]["band"] == "pass"
    assert payload["gate_decision"]["decision"] == "pass"


def test_agent_endpoint_returns_needs_review_when_support_is_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")
    monkeypatch.setattr(
        agent_workflow,
        "answer_document_question",
        lambda **kwargs: QuestionAnswerResult(
            question=str(kwargs["question"]),
            answer="Insufficient evidence to answer the question from retrieved context.",
            status="insufficient_evidence",
            citations=[],
        ),
    )

    response = _agent(document_id, {"instruction": "What was free cash flow?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_review"
    assert payload["selected_tools"] == ["ask"]
    assert payload["outputs_withheld"] is True
    assert payload["trace"]["status"] == "needs_review"
    assert payload["gate_decision"]["decision"] == "review"
    assert payload["outputs"] == {}
    assert len(payload["decision_reasons"]) >= 2
    assert any("withheld" in reason.lower() for reason in payload["decision_reasons"])
    _assert_trace_structure(
        trace=payload["trace"],
        expected_status="needs_review",
        expected_document_id=document_id,
        expected_tool_name="ask",
        expected_tool_status="succeeded",
    )


def test_agent_endpoint_returns_blocked_when_document_not_ready() -> None:
    document_id = _seed_document(status="uploaded")

    response = _agent(document_id, {"instruction": "Generate a memo for this document."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["selected_tools"] == ["memo"]
    assert payload["outputs_withheld"] is True
    assert payload["outputs"] == {}
    assert payload["gate_decision"]["decision"] == "block"
    assert payload["decision_reasons"]
    _assert_trace_structure(
        trace=payload["trace"],
        expected_status="blocked",
        expected_document_id=document_id,
        expected_tool_name="document_ready_check",
        expected_tool_status="blocked",
    )
    assert payload["trace"]["tool_calls"][0]["error"] is not None


def test_agent_endpoint_selects_only_requested_tools_and_executes_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")
    fake_workflow_service = FakeStructuredWorkflowService()
    monkeypatch.setattr(
        documents_routes,
        "get_constrained_research_agent",
        lambda: agent_workflow.ConstrainedResearchAgent(
            workflow_service_factory=lambda: fake_workflow_service
        ),
    )

    response = _agent(
        document_id,
        {"instruction": "Extract KPIs and risks from this document."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["selected_tools"] == ["extract_kpis", "extract_risks"]
    assert payload["outputs_withheld"] is False
    assert payload["decision_reasons"] == []
    assert set(payload["outputs"].keys()) == {"extract_kpis", "extract_risks"}
    assert payload["gate_decision"]["decision"] == "pass"
    assert fake_workflow_service.calls == ["extract_kpis", "extract_risks"]


def test_agent_endpoint_returns_404_for_missing_document() -> None:
    response = _agent(999, {"instruction": "What happened to revenue?"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_agent_endpoint_returns_deterministic_trace_id_for_same_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")
    monkeypatch.setattr(
        agent_workflow,
        "answer_document_question",
        lambda **kwargs: QuestionAnswerResult(
            question=str(kwargs["question"]),
            answer="Insufficient evidence to answer the question from retrieved context.",
            status="insufficient_evidence",
            citations=[],
        ),
    )

    first_response = _agent(document_id, {"instruction": "What was free cash flow?"})
    second_response = _agent(document_id, {"instruction": "What was free cash flow?"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_trace_id = first_response.json()["trace"]["trace_id"]
    second_trace_id = second_response.json()["trace"]["trace_id"]
    assert first_trace_id == second_trace_id
