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
from app.workflows.schemas import MemoCitationsBySection, MemoDraft
from app.workflows.service import StructuredWorkflowService


class FakeLLMProvider:
    def __init__(self, memo_draft: MemoDraft) -> None:
        self.memo_draft = memo_draft
        self.call_count = 0

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
    ) -> MemoDraft:
        self.call_count += 1
        return self.memo_draft


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


def _memo(document_id: int, payload: dict[str, object] | None = None) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            if payload is None:
                return await client.post(f"/documents/{document_id}/memo")
            return await client.post(f"/documents/{document_id}/memo", json=payload)

    return asyncio.run(request())


def _retrieved_chunk(chunk_index: int, text: str, similarity: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_index=chunk_index,
        page_number=1,
        text=text,
        token_count=20,
        similarity=similarity,
    )


def test_memo_endpoint_returns_generated_structured_memo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")

    fake_llm_provider = FakeLLMProvider(
        MemoDraft(
            company_overview="Acme Corp provides enterprise analytics software.",
            key_developments=["Revenue growth accelerated in Q4."],
            risks=["Foreign exchange exposure can pressure margins."],
            catalysts=["Upcoming product launch can support growth."],
            kpis=["Revenue +12% year over year."],
            open_questions=["Can expansion sustain double-digit growth?"],
            citations_by_section=MemoCitationsBySection(
                company_overview=["C1"],
                key_developments=["C1"],
                risks=["C2"],
                catalysts=["C1"],
                kpis=["C1"],
                open_questions=["C2"],
            ),
        )
    )

    monkeypatch.setattr(
        documents_routes,
        "get_structured_workflow_service",
        lambda: StructuredWorkflowService(
            llm_provider=fake_llm_provider,
            max_workflow_citations=3,
            max_workflow_items=8,
        ),
    )

    def fake_retrieve_relevant_chunks(**kwargs: Any) -> list[RetrievedChunk]:
        assert kwargs["document_id"] == document_id
        return [
            _retrieved_chunk(0, "Revenue increased 12 percent in Q4.", 0.94),
            _retrieved_chunk(1, "FX exposure remains a margin risk.", 0.87),
        ]

    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        fake_retrieve_relevant_chunks,
    )

    response = _memo(document_id, {"instruction": "Create a grounded investment memo."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "generated"

    memo = payload["memo"]
    assert set(memo.keys()) == {
        "company_overview",
        "key_developments",
        "risks",
        "catalysts",
        "kpis",
        "open_questions",
        "citations_by_section",
    }
    assert memo["company_overview"].startswith("Acme Corp")
    assert memo["key_developments"]
    assert memo["risks"]
    assert memo["catalysts"]
    assert memo["kpis"]
    assert memo["open_questions"]
    assert set(memo["citations_by_section"].keys()) == {
        "company_overview",
        "key_developments",
        "risks",
        "catalysts",
        "kpis",
        "open_questions",
    }
    assert fake_llm_provider.call_count == 1


def test_memo_endpoint_returns_insufficient_evidence_when_context_is_weak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document(status="ready")

    fake_llm_provider = FakeLLMProvider(
        MemoDraft(
            company_overview="placeholder",
            key_developments=["placeholder"],
            risks=["placeholder"],
            catalysts=["placeholder"],
            kpis=["placeholder"],
            open_questions=["placeholder"],
            citations_by_section=MemoCitationsBySection(
                company_overview=["C1"],
                key_developments=["C1"],
                risks=["C1"],
                catalysts=["C1"],
                kpis=["C1"],
                open_questions=["C1"],
            ),
        )
    )

    monkeypatch.setattr(
        documents_routes,
        "get_structured_workflow_service",
        lambda: StructuredWorkflowService(llm_provider=fake_llm_provider),
    )
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **kwargs: [],
    )

    response = _memo(document_id, {"instruction": "Create memo."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "insufficient_evidence"
    assert payload["memo"] is None
    assert fake_llm_provider.call_count == 0


def test_memo_endpoint_returns_400_when_document_not_ready() -> None:
    document_id = _seed_document(status="uploaded")

    response = _memo(document_id, {"instruction": "Create memo."})

    assert response.status_code == 400
    assert "processed and ready" in response.json()["detail"]


def test_memo_endpoint_returns_404_for_missing_document() -> None:
    response = _memo(999, {"instruction": "Create memo."})

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}
