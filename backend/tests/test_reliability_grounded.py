import pytest

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.qa.service import Citation
from app.reliability.grounded import GroundedAskReliabilityEvaluator


def _embedding(first: float, second: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = first
    vector[1] = second
    return vector


@pytest.fixture
def document_with_chunks() -> tuple[int, int]:
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
            text="Revenue was 120 in Q4 and margin was stable.",
            token_count=10,
            embedding=_embedding(1.0, 0.0),
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return document.id, chunk.chunk_index
    finally:
        db.close()


def test_grounded_evaluator_passes_when_citations_are_grounded(
    document_with_chunks: tuple[int, int],
) -> None:
    document_id, chunk_index = document_with_chunks
    db = SessionLocal()
    evaluator = GroundedAskReliabilityEvaluator()
    try:
        result = evaluator.evaluate(
            db=db,
            document_id=document_id,
            answer="Revenue was 120 in Q4. [C1]",
            citations=[
                Citation(
                    citation_id="C1",
                    rank=1,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    page_number=1,
                    text_excerpt="Revenue was 120 in Q4 and margin was stable.",
                    retrieval_score=0.92,
                )
            ],
        )
    finally:
        db.close()

    assessment = result.assessment
    assert assessment.verification.status == "passed"
    assert assessment.confidence.band == "pass"
    assert assessment.gate_decision.allow_execution is True
    assert assessment.issues == []
    assert result.unsupported_numeric_claims == []


def test_grounded_evaluator_reports_missing_grounding_and_numeric_claims(
    document_with_chunks: tuple[int, int],
) -> None:
    document_id, _ = document_with_chunks
    db = SessionLocal()
    evaluator = GroundedAskReliabilityEvaluator()
    try:
        result = evaluator.evaluate(
            db=db,
            document_id=document_id,
            answer="Revenue was 999 in Q4. [C1]",
            citations=[
                Citation(
                    citation_id="C1",
                    rank=1,
                    document_id=999,
                    chunk_index=99,
                    page_number=1,
                    text_excerpt="Does not exist in any stored chunk.",
                    retrieval_score=0.2,
                )
            ],
        )
    finally:
        db.close()

    assessment = result.assessment
    assert assessment.verification.status == "failed"
    assert assessment.gate_decision.decision == "block"
    assert assessment.gate_decision.allow_execution is False
    assert "Unsupported numeric claims detected" in " ".join(assessment.issues)
    assert result.unsupported_numeric_claims == ["999"]
