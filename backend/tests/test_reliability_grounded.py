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


def test_grounded_evaluator_reports_partial_citation_verification_scores(
    document_with_chunks: tuple[int, int],
) -> None:
    document_id, chunk_index = document_with_chunks
    db = SessionLocal()
    evaluator = GroundedAskReliabilityEvaluator()
    try:
        result = evaluator.evaluate(
            db=db,
            document_id=document_id,
            answer="Revenue was 120 in Q4. [C1] [C2]",
            citations=[
                Citation(
                    citation_id="C1",
                    rank=1,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    page_number=1,
                    text_excerpt="Revenue was 120 in Q4 and margin was stable.",
                    retrieval_score=0.9,
                ),
                Citation(
                    citation_id="C2",
                    rank=2,
                    document_id=999,
                    chunk_index=999,
                    page_number=1,
                    text_excerpt="Unsupported excerpt.",
                    retrieval_score=0.2,
                ),
            ],
        )
    finally:
        db.close()

    checks = {
        check.check_name: check for check in result.assessment.verification.checks
    }
    assert checks["citation_exists"].score == pytest.approx(0.5)
    assert checks["citation_document_match"].score == pytest.approx(0.5)
    assert checks["citation_excerpt_in_chunk"].score == pytest.approx(0.5)
    assert checks["citation_exists"].citation_ids == ["C1"]
    assert checks["citation_document_match"].citation_ids == ["C1"]
    assert checks["citation_excerpt_in_chunk"].citation_ids == ["C1"]
    assert result.assessment.verification.status == "failed"
    assert result.assessment.gate_decision.decision == "block"


def test_grounded_evaluator_builds_deterministic_confidence_signals(
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
                    retrieval_score=0.0,
                )
            ],
        )
    finally:
        db.close()

    confidence = result.assessment.confidence
    signal_by_name = {signal.signal_name: signal for signal in confidence.signals}
    assert signal_by_name["supporting_citation_count"].value == pytest.approx(0.333333)
    assert signal_by_name["retrieval_score_quality"].value == pytest.approx(0.5)
    assert signal_by_name["verification_outcome"].value == pytest.approx(1.0)
    assert signal_by_name["unsupported_numeric_claims"].value == pytest.approx(1.0)
    assert confidence.score == pytest.approx(0.8375)
    assert confidence.band == "pass"
