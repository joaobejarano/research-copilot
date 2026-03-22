from typing import Any

import pytest

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.retrieval import service as retrieval_service
from app.workflows.schemas import (
    KPIDraft,
    KPIExtractionOutput,
    KPIExtractionRequest,
    KPIItem,
    MemoCitationsBySection,
    MemoDraft,
    MemoGenerationOutput,
    MemoGenerationRequest,
    RiskDraft,
    RiskExtractionOutput,
    RiskExtractionRequest,
    RiskItem,
    TimelineBuildingOutput,
    TimelineBuildingRequest,
    TimelineDraft,
    TimelineEvent,
)
from app.workflows.service import StructuredWorkflowService


class FakeEmbeddingProvider:
    def __init__(self, query_embedding: list[float]) -> None:
        self.query_embedding = query_embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.query_embedding for _ in texts]


class FakeLLMProvider:
    def __init__(self, responses: dict[type[Any], Any]) -> None:
        self.responses = responses
        self.calls: list[type[Any]] = []

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
    ) -> Any:
        self.calls.append(response_model)
        return self.responses[response_model]


def _embedding(first: float, second: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = first
    vector[1] = second
    return vector


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def ready_document_id() -> int:
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

        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    page_number=1,
                    text="Revenue grew to 120M with stable margins.",
                    token_count=8,
                    embedding=_embedding(1.0, 0.0),
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=1,
                    page_number=2,
                    text="Management highlighted FX volatility as a risk.",
                    token_count=8,
                    embedding=_embedding(0.9, 0.1),
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=2,
                    page_number=3,
                    text="A product launch is planned for next quarter.",
                    token_count=9,
                    embedding=_embedding(0.0, 1.0),
                ),
            ]
        )
        db.commit()
        return document.id
    finally:
        db.close()


def test_generate_memo_with_real_retrieval_includes_schema_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
    db_session,
    ready_document_id: int,
) -> None:
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_embedding(1.0, 0.0)),
    )
    fake_llm = FakeLLMProvider(
        {
            MemoDraft: MemoDraft(
                company_overview="Acme Corp sells enterprise analytics software.",
                key_developments=["Revenue reached 120M in Q4."],
                risks=["FX volatility may pressure margins."],
                catalysts=["Product launch planned for next quarter."],
                kpis=["Revenue 120M."],
                open_questions=["Will FX pressure persist in H1?"],
                citations_by_section=MemoCitationsBySection(
                    company_overview=["C1"],
                    key_developments=["C1"],
                    risks=["C2"],
                    catalysts=["C2"],
                    kpis=["C1"],
                    open_questions=["C2"],
                ),
            )
        }
    )
    service = StructuredWorkflowService(
        llm_provider=fake_llm,
        max_workflow_citations=2,
        max_workflow_items=8,
    )

    result = service.generate_memo(
        db=db_session,
        request=MemoGenerationRequest(
            document_id=ready_document_id,
            instruction="Generate a grounded investment memo.",
            top_k=2,
            min_similarity=0.2,
        ),
    )
    validated = MemoGenerationOutput.model_validate(result.model_dump())

    assert validated.status == "generated"
    assert validated.memo is not None
    assert len(validated.evidence.citations) == 2
    assert validated.evidence.citations[0].citation_id == "C1"
    assert set(validated.evidence.citations[0].model_dump().keys()) == {
        "citation_id",
        "rank",
        "document_id",
        "chunk_index",
        "page_number",
        "text_excerpt",
        "retrieval_score",
    }
    assert fake_llm.calls == [MemoDraft]


def test_extract_kpis_with_real_retrieval_includes_schema_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
    db_session,
    ready_document_id: int,
) -> None:
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_embedding(1.0, 0.0)),
    )
    fake_llm = FakeLLMProvider(
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
    service = StructuredWorkflowService(llm_provider=fake_llm, max_workflow_citations=2)

    result = service.extract_kpis(
        db=db_session,
        request=KPIExtractionRequest(
            document_id=ready_document_id,
            instruction="Extract KPIs.",
            top_k=2,
            min_similarity=0.2,
        ),
    )
    validated = KPIExtractionOutput.model_validate(result.model_dump())

    assert validated.status == "completed"
    assert len(validated.kpis) == 1
    assert validated.kpis[0].citation == "C1"
    assert len(validated.evidence.citations) == 2
    assert fake_llm.calls == [KPIDraft]


def test_extract_risks_with_real_retrieval_includes_schema_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
    db_session,
    ready_document_id: int,
) -> None:
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_embedding(1.0, 0.0)),
    )
    fake_llm = FakeLLMProvider(
        {
            RiskDraft: RiskDraft(
                risks=[
                    RiskItem(
                        title="FX volatility",
                        description="Currency swings may compress margins.",
                        severity_or_materiality="medium",
                        citation="C2",
                    )
                ]
            )
        }
    )
    service = StructuredWorkflowService(llm_provider=fake_llm, max_workflow_citations=2)

    result = service.extract_risks(
        db=db_session,
        request=RiskExtractionRequest(
            document_id=ready_document_id,
            instruction="Extract risks.",
            top_k=2,
            min_similarity=0.2,
        ),
    )
    validated = RiskExtractionOutput.model_validate(result.model_dump())

    assert validated.status == "completed"
    assert len(validated.risks) == 1
    assert validated.risks[0].citation == "C2"
    assert len(validated.evidence.citations) == 2
    assert fake_llm.calls == [RiskDraft]


def test_build_timeline_with_real_retrieval_includes_schema_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
    db_session,
    ready_document_id: int,
) -> None:
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_embedding(1.0, 0.0)),
    )
    fake_llm = FakeLLMProvider(
        {
            TimelineDraft: TimelineDraft(
                events=[
                    TimelineEvent(
                        event_date_or_period="2024-Q4",
                        event_summary="Revenue re-accelerated in Q4.",
                        citation="C1",
                    )
                ]
            )
        }
    )
    service = StructuredWorkflowService(llm_provider=fake_llm, max_workflow_citations=2)

    result = service.build_timeline(
        db=db_session,
        request=TimelineBuildingRequest(
            document_id=ready_document_id,
            instruction="Build timeline.",
            top_k=2,
            min_similarity=0.2,
        ),
    )
    validated = TimelineBuildingOutput.model_validate(result.model_dump())

    assert validated.status == "completed"
    assert len(validated.events) == 1
    assert validated.events[0].citation == "C1"
    assert len(validated.evidence.citations) == 2
    assert fake_llm.calls == [TimelineDraft]

