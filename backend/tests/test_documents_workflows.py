import asyncio
from typing import Any

import httpx
import pytest

from app.api.routes import documents as documents_routes
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.main import app
from app.retrieval.service import RetrievedChunk
from app.workflows import service as workflow_service
from app.workflows.schemas import (
    KPIDraft,
    KPIItem,
    RiskDraft,
    RiskItem,
    TimelineDraft,
    TimelineEvent,
)
from app.workflows.service import StructuredWorkflowService


class FakeWorkflowLLMProvider:
    def __init__(self, responses: dict[type[Any], Any]) -> None:
        self.responses = responses
        self.call_count = 0

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
    ) -> Any:
        self.call_count += 1
        return self.responses[response_model]


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


def _retrieved_chunk(chunk_index: int, text: str, similarity: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_index=chunk_index,
        page_number=1,
        text=text,
        token_count=20,
        similarity=similarity,
    )


def _post(path: str, payload: dict[str, object] | None = None) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            if payload is None:
                return await client.post(path)
            return await client.post(path, json=payload)

    return asyncio.run(request())


def test_extract_kpis_endpoint_returns_completed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")

    fake_llm_provider = FakeWorkflowLLMProvider(
        {
            KPIDraft: KPIDraft(
                kpis=[
                    KPIItem(
                        name="Revenue",
                        value="120M",
                        unit="USD",
                        period="2024-Q4",
                        citation="C1",
                    )
                ]
            )
        }
    )
    monkeypatch.setattr(
        documents_routes,
        "get_structured_workflow_service",
        lambda: StructuredWorkflowService(llm_provider=fake_llm_provider),
    )
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **kwargs: [_retrieved_chunk(0, "Revenue reached 120M.", 0.91)],
    )

    response = _post(
        f"/documents/{document_id}/extract/kpis",
        {"instruction": "Extract KPIs."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "completed"
    assert payload["workflow"] == "kpi_extraction"
    assert payload["kpis"][0]["name"] == "Revenue"
    assert payload["kpis"][0]["citation"] == "C1"
    assert payload["evidence"]["citations"][0]["citation_id"] == "C1"
    assert fake_llm_provider.call_count == 1


def test_extract_risks_endpoint_returns_completed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")

    fake_llm_provider = FakeWorkflowLLMProvider(
        {
            RiskDraft: RiskDraft(
                risks=[
                    RiskItem(
                        title="FX volatility",
                        description="Currency moves may pressure margins.",
                        severity_or_materiality="medium",
                        citation="C1",
                    )
                ]
            )
        }
    )
    monkeypatch.setattr(
        documents_routes,
        "get_structured_workflow_service",
        lambda: StructuredWorkflowService(llm_provider=fake_llm_provider),
    )
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **kwargs: [_retrieved_chunk(0, "Management noted FX risk.", 0.9)],
    )

    response = _post(
        f"/documents/{document_id}/extract/risks",
        {"instruction": "Extract risks."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "completed"
    assert payload["workflow"] == "risk_extraction"
    assert payload["risks"][0]["title"] == "FX volatility"
    assert payload["risks"][0]["citation"] == "C1"
    assert payload["evidence"]["citations"][0]["citation_id"] == "C1"
    assert fake_llm_provider.call_count == 1


def test_timeline_endpoint_returns_completed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")

    fake_llm_provider = FakeWorkflowLLMProvider(
        {
            TimelineDraft: TimelineDraft(
                events=[
                    TimelineEvent(
                        event_date_or_period="2024-Q4",
                        event_summary="Revenue re-accelerated after prior softness.",
                        citation="C1",
                    )
                ]
            )
        }
    )
    monkeypatch.setattr(
        documents_routes,
        "get_structured_workflow_service",
        lambda: StructuredWorkflowService(llm_provider=fake_llm_provider),
    )
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **kwargs: [_retrieved_chunk(0, "Q4 results showed renewed momentum.", 0.88)],
    )

    response = _post(
        f"/documents/{document_id}/timeline",
        {"instruction": "Build timeline."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "completed"
    assert payload["workflow"] == "timeline_building"
    assert payload["events"][0]["event_date_or_period"] == "2024-Q4"
    assert payload["events"][0]["citation"] == "C1"
    assert payload["evidence"]["citations"][0]["citation_id"] == "C1"
    assert fake_llm_provider.call_count == 1


@pytest.mark.parametrize(
    ("path", "result_field"),
    [
        ("extract/kpis", "kpis"),
        ("extract/risks", "risks"),
        ("timeline", "events"),
    ],
)
def test_workflow_endpoints_return_insufficient_evidence_when_no_chunks(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    result_field: str,
) -> None:
    document_id = _seed_document(status="ready")

    fake_llm_provider = FakeWorkflowLLMProvider(
        {
            KPIDraft: KPIDraft(kpis=[]),
            RiskDraft: RiskDraft(risks=[]),
            TimelineDraft: TimelineDraft(events=[]),
        }
    )
    monkeypatch.setattr(
        documents_routes,
        "get_structured_workflow_service",
        lambda: StructuredWorkflowService(llm_provider=fake_llm_provider),
    )
    monkeypatch.setattr(workflow_service, "retrieve_relevant_chunks", lambda **kwargs: [])

    response = _post(f"/documents/{document_id}/{path}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "insufficient_evidence"
    assert payload[result_field] == []
    assert payload["evidence"]["citations"] == []
    assert fake_llm_provider.call_count == 0


@pytest.mark.parametrize(
    ("path", "detail_fragment"),
    [
        ("extract/kpis", "before KPI extraction"),
        ("extract/risks", "before risk extraction"),
        ("timeline", "before timeline building"),
    ],
)
def test_workflow_endpoints_require_ready_document(
    path: str,
    detail_fragment: str,
) -> None:
    document_id = _seed_document(status="uploaded")

    response = _post(f"/documents/{document_id}/{path}")

    assert response.status_code == 400
    assert detail_fragment in response.json()["detail"]


@pytest.mark.parametrize(
    "path",
    [
        "extract/kpis",
        "extract/risks",
        "timeline",
    ],
)
def test_workflow_endpoints_return_404_for_missing_document(path: str) -> None:
    response = _post(f"/documents/999/{path}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}
