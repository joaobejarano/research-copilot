import os
from pathlib import Path

import pytest

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.ingestion.processing import get_embedding_provider, process_uploaded_document


class FakeEmbeddingProvider:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index + 1)] * self.dimension for index, _ in enumerate(texts)]


def _create_uploaded_txt_document(db_path_text: str) -> tuple[int, Path]:
    db = SessionLocal()
    try:
        document = Document(
            company_name="Acme Corp",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="pending",
            status="uploaded",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        relative_storage_path = (
            Path("Acme_Corp")
            / "financial_report"
            / "2024-Q4"
            / f"{document.id}.txt"
        )
        absolute_storage_path = Path(os.environ["STORAGE_DIR"]) / relative_storage_path
        absolute_storage_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_storage_path.write_text(db_path_text, encoding="utf-8")

        document.storage_path = str(relative_storage_path)
        db.commit()
        db.refresh(document)
        return document.id, absolute_storage_path
    finally:
        db.close()


def test_process_uploaded_document_persists_embedded_chunks() -> None:
    document_id, _ = _create_uploaded_txt_document("one two three four five six")
    db = SessionLocal()

    try:
        persisted_count = process_uploaded_document(
            db=db,
            document_id=document_id,
            embedding_provider=FakeEmbeddingProvider(EMBEDDING_DIMENSION),
            chunk_size=3,
            chunk_overlap=1,
        )

        stored_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

        assert persisted_count == 3
        assert len(stored_chunks) == 3
        assert stored_chunks[0].chunk_index == 0
        assert stored_chunks[0].page_number is None
        assert stored_chunks[0].token_count == 3
        assert stored_chunks[0].text == "one two three"
        assert stored_chunks[0].embedding is not None
        assert len(stored_chunks[0].embedding) == EMBEDDING_DIMENSION
    finally:
        db.close()


def test_process_uploaded_document_fails_on_dimension_mismatch() -> None:
    document_id, _ = _create_uploaded_txt_document("one two three four")
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            process_uploaded_document(
                db=db,
                document_id=document_id,
                embedding_provider=FakeEmbeddingProvider(EMBEDDING_DIMENSION - 1),
                chunk_size=2,
                chunk_overlap=0,
            )

        persisted_count = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .count()
        )
        assert persisted_count == 0
    finally:
        db.close()


def test_get_embedding_provider_rejects_unsupported_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        get_embedding_provider(provider_name="remote")
