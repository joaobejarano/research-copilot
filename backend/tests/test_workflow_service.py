from typing import Any

import pytest

from app.retrieval.service import RetrievedChunk
from app.workflows import service as workflow_service
from app.workflows.schemas import (
    MemoCitationsBySection,
    KPIDraft,
    KPIExtractionRequest,
    KPIItem,
    MemoDraft,
    MemoGenerationRequest,
    RiskDraft,
    RiskExtractionRequest,
    RiskItem,
    TimelineBuildingRequest,
    TimelineDraft,
    TimelineEvent,
)
from app.workflows.service import StructuredWorkflowService


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


def _chunk(index: int, text: str, similarity: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_index=index,
        page_number=1,
        text=text,
        token_count=12,
        similarity=similarity,
    )


def test_generate_memo_returns_insufficient_evidence_when_no_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_provider = FakeLLMProvider({})
    service = StructuredWorkflowService(llm_provider=fake_provider)
    monkeypatch.setattr(workflow_service, "retrieve_relevant_chunks", lambda **_: [])

    result = service.generate_memo(
        db=None,  # type: ignore[arg-type]
        request=MemoGenerationRequest(
            document_id=1,
            instruction="Create a short memo.",
        ),
    )

    assert result.status == "insufficient_evidence"
    assert result.memo is None
    assert result.evidence.citations == []
    assert fake_provider.calls == []


def test_generate_memo_returns_completed_with_retrieved_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_provider = FakeLLMProvider(
        {
            MemoDraft: MemoDraft(
                company_overview="Acme provides enterprise software tools.",
                key_developments=["Revenue grew in Q4."],
                risks=["FX volatility remains a pressure point."],
                catalysts=["New product release in Q1."],
                kpis=["Revenue +12% YoY."],
                open_questions=["Can growth persist above 10%?"],
                citations_by_section=MemoCitationsBySection(
                    company_overview=["C1"],
                    key_developments=["C1"],
                    risks=["C2"],
                    catalysts=["C1"],
                    kpis=["C1"],
                    open_questions=["C2"],
                ),
            )
        }
    )
    service = StructuredWorkflowService(llm_provider=fake_provider, max_workflow_citations=2)
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **_: [_chunk(0, "Revenue grew in Q4."), _chunk(1, "Margins were stable.")],
    )

    result = service.generate_memo(
        db=None,  # type: ignore[arg-type]
        request=MemoGenerationRequest(document_id=42, instruction="Generate memo"),
    )

    assert result.status == "generated"
    assert result.memo is not None
    assert result.memo.company_overview.startswith("Acme")
    assert len(result.evidence.citations) == 2
    assert [citation.citation_id for citation in result.evidence.citations] == ["C1", "C2"]


def test_generate_memo_rejects_unknown_citation_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_provider = FakeLLMProvider(
        {
            MemoDraft: MemoDraft(
                company_overview="Overview",
                key_developments=["One development."],
                risks=["One risk."],
                catalysts=["One catalyst."],
                kpis=["One KPI."],
                open_questions=["One question."],
                citations_by_section=MemoCitationsBySection(
                    company_overview=["C3"],
                    key_developments=["C3"],
                    risks=["C3"],
                    catalysts=["C3"],
                    kpis=["C3"],
                    open_questions=["C3"],
                ),
            )
        }
    )
    service = StructuredWorkflowService(llm_provider=fake_provider, max_workflow_citations=1)
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **_: [_chunk(0, "Only one chunk.")],
    )

    with pytest.raises(ValueError, match="unknown citation_id"):
        service.generate_memo(
            db=None,  # type: ignore[arg-type]
            request=MemoGenerationRequest(document_id=1, instruction="Generate memo"),
        )


def test_extract_kpis_returns_completed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_provider = FakeLLMProvider(
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
    service = StructuredWorkflowService(llm_provider=fake_provider)
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **_: [_chunk(0, "Revenue increased to 120M in Q4.")],
    )

    result = service.extract_kpis(
        db=None,  # type: ignore[arg-type]
        request=KPIExtractionRequest(document_id=9, instruction="Extract key KPIs."),
    )

    assert result.status == "completed"
    assert len(result.kpis) == 1
    assert result.kpis[0].name == "Revenue"


def test_extract_risks_returns_completed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_provider = FakeLLMProvider(
        {
            RiskDraft: RiskDraft(
                risks=[
                    RiskItem(
                        title="FX volatility",
                        description="Currency movements can pressure earnings.",
                        severity_or_materiality="medium",
                        citation="C1",
                    )
                ]
            )
        }
    )
    service = StructuredWorkflowService(llm_provider=fake_provider)
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **_: [_chunk(0, "FX swings were highlighted as a near-term risk.")],
    )

    result = service.extract_risks(
        db=None,  # type: ignore[arg-type]
        request=RiskExtractionRequest(document_id=11, instruction="Extract key risks."),
    )

    assert result.status == "completed"
    assert len(result.risks) == 1
    assert result.risks[0].title == "FX volatility"


def test_build_timeline_returns_completed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_provider = FakeLLMProvider(
        {
            TimelineDraft: TimelineDraft(
                events=[
                    TimelineEvent(
                        event_date_or_period="2024-Q4",
                        event_summary="Revenue rebounded after prior slowdown.",
                        citation="C1",
                    )
                ]
            )
        }
    )
    service = StructuredWorkflowService(llm_provider=fake_provider)
    monkeypatch.setattr(
        workflow_service,
        "retrieve_relevant_chunks",
        lambda **_: [_chunk(0, "Q4 showed a clear revenue rebound.")],
    )

    result = service.build_timeline(
        db=None,  # type: ignore[arg-type]
        request=TimelineBuildingRequest(document_id=13, instruction="Build a timeline."),
    )

    assert result.status == "completed"
    assert len(result.events) == 1
    assert result.events[0].event_date_or_period == "2024-Q4"
