import pytest

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.retrieval import service as retrieval_service


class FakeEmbeddingProvider:
    def __init__(self, query_embedding: list[float]) -> None:
        self.query_embedding = query_embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.query_embedding for _ in texts]


def _make_embedding(first: float, second: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = first
    vector[1] = second
    return vector


def _seed_documents_and_chunks() -> tuple[int, int]:
    db = SessionLocal()
    try:
        document_one = Document(
            company_name="Acme Corp",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="Acme_Corp/financial_report/2024-Q4/1.txt",
            status="ready",
        )
        document_two = Document(
            company_name="Globex",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="Globex/financial_report/2024-Q4/2.txt",
            status="ready",
        )
        db.add_all([document_one, document_two])
        db.commit()
        db.refresh(document_one)
        db.refresh(document_two)

        db.add_all(
            [
                DocumentChunk(
                    document_id=document_one.id,
                    chunk_index=0,
                    page_number=1,
                    text="alpha",
                    token_count=1,
                    embedding=_make_embedding(1.0, 0.0),
                ),
                DocumentChunk(
                    document_id=document_one.id,
                    chunk_index=1,
                    page_number=1,
                    text="alpha beta",
                    token_count=2,
                    embedding=_make_embedding(0.8, 0.2),
                ),
                DocumentChunk(
                    document_id=document_one.id,
                    chunk_index=2,
                    page_number=2,
                    text="beta",
                    token_count=1,
                    embedding=_make_embedding(0.0, 1.0),
                ),
                DocumentChunk(
                    document_id=document_two.id,
                    chunk_index=0,
                    page_number=1,
                    text="other document chunk",
                    token_count=3,
                    embedding=_make_embedding(1.0, 0.0),
                ),
            ]
        )
        db.commit()

        return document_one.id, document_two.id
    finally:
        db.close()


def test_retrieve_relevant_chunks_returns_ranked_document_scoped_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, _ = _seed_documents_and_chunks()
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )
    db = SessionLocal()

    try:
        results = retrieval_service.retrieve_relevant_chunks(
            db=db,
            document_id=document_id,
            question="alpha performance",
            top_k=2,
            min_similarity=0.5,
        )

        assert len(results) == 2
        assert [result.chunk_index for result in results] == [0, 1]
        assert results[0].similarity >= results[1].similarity
    finally:
        db.close()


def test_retrieve_relevant_chunks_rejects_missing_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="was not found"):
            retrieval_service.retrieve_relevant_chunks(
                db=db,
                document_id=999,
                question="alpha",
            )
    finally:
        db.close()


def test_retrieve_relevant_chunks_rejects_empty_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, _ = _seed_documents_and_chunks()
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="question must not be empty"):
            retrieval_service.retrieve_relevant_chunks(
                db=db,
                document_id=document_id,
                question="   ",
            )
    finally:
        db.close()


def test_retrieve_relevant_chunks_validates_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, _ = _seed_documents_and_chunks()
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="top_k must be greater than 0"):
            retrieval_service.retrieve_relevant_chunks(
                db=db,
                document_id=document_id,
                question="alpha",
                top_k=0,
            )
        with pytest.raises(ValueError, match="min_similarity must be between -1 and 1"):
            retrieval_service.retrieve_relevant_chunks(
                db=db,
                document_id=document_id,
                question="alpha",
                min_similarity=2.0,
            )
    finally:
        db.close()
