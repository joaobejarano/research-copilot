import pytest
from pydantic import ValidationError

from app.core.config import MAX_WORKFLOW_CITATIONS, MAX_WORKFLOW_ITEMS
from app.workflows.schemas import (
    MemoGenerationRequest,
    TimelineBuildingOutput,
    WorkflowCitation,
    WorkflowEvidence,
)


def test_workflow_citation_rejects_invalid_citation_id() -> None:
    with pytest.raises(ValidationError):
        WorkflowCitation(
            citation_id="citation-1",
            rank=1,
            document_id=1,
            chunk_index=0,
            page_number=1,
            text_excerpt="excerpt",
            retrieval_score=0.9,
        )


def test_memo_generation_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MemoGenerationRequest(
            document_id=1,
            instruction="Draft an analyst memo",
            unknown_field="not-allowed",
        )


def test_workflow_evidence_respects_max_citations() -> None:
    citations = [
        WorkflowCitation(
            citation_id=f"C{index + 1}",
            rank=index + 1,
            document_id=1,
            chunk_index=index,
            page_number=1,
            text_excerpt=f"excerpt-{index}",
            retrieval_score=0.8,
        )
        for index in range(MAX_WORKFLOW_CITATIONS + 1)
    ]

    with pytest.raises(ValidationError):
        WorkflowEvidence(citations=citations)


def test_timeline_output_forbids_more_than_max_items() -> None:
    oversized_events = [
        {
            "event_date_or_period": f"2024-Q{index + 1}",
            "event_summary": "summary",
            "citation": "C1",
        }
        for index in range(MAX_WORKFLOW_ITEMS + 1)
    ]

    with pytest.raises(ValidationError):
        TimelineBuildingOutput(
            document_id=1,
            status="completed",
            events=oversized_events,
            evidence={"citations": []},
        )
