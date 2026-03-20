import asyncio

import httpx

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.main import app


def _get_document_chunks(document_id: int) -> httpx.Response:
    async def request_chunks() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(f"/documents/{document_id}/chunks")

    return asyncio.run(request_chunks())


def _create_document_with_chunks() -> int:
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
                    chunk_index=2,
                    page_number=2,
                    text="third chunk",
                    token_count=2,
                    embedding=[0.3] * EMBEDDING_DIMENSION,
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    page_number=1,
                    text="first chunk",
                    token_count=2,
                    embedding=[0.1] * EMBEDDING_DIMENSION,
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=1,
                    page_number=1,
                    text="second chunk",
                    token_count=2,
                    embedding=[0.2] * EMBEDDING_DIMENSION,
                ),
            ]
        )
        db.commit()
        return document.id
    finally:
        db.close()


def _create_document_without_chunks() -> int:
    db = SessionLocal()
    try:
        document = Document(
            company_name="Acme Corp",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="Acme_Corp/financial_report/2024-Q4/1.txt",
            status="uploaded",
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document.id
    finally:
        db.close()


def test_get_document_chunks_returns_sorted_chunks_without_embeddings() -> None:
    document_id = _create_document_with_chunks()

    response = _get_document_chunks(document_id)

    assert response.status_code == 200
    payload = response.json()

    assert payload["document_id"] == document_id
    assert payload["status"] == "ready"
    assert payload["chunk_count"] == 3
    assert payload["embedding_dimension"] == EMBEDDING_DIMENSION
    assert [chunk["chunk_index"] for chunk in payload["chunks"]] == [0, 1, 2]
    assert payload["chunks"][0] == {
        "chunk_index": 0,
        "page_number": 1,
        "text": "first chunk",
        "token_count": 2,
    }
    assert "embedding" not in payload["chunks"][0]


def test_get_document_chunks_returns_empty_list_when_no_chunks() -> None:
    document_id = _create_document_without_chunks()

    response = _get_document_chunks(document_id)

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["status"] == "uploaded"
    assert payload["chunk_count"] == 0
    assert payload["embedding_dimension"] == EMBEDDING_DIMENSION
    assert payload["chunks"] == []


def test_get_document_chunks_returns_404_for_missing_document() -> None:
    response = _get_document_chunks(999)

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}
