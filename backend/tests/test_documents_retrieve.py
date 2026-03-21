import asyncio

import httpx
import pytest

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.main import app
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


def _seed_document_with_chunks() -> tuple[int, int]:
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
        other_document = Document(
            company_name="Globex",
            document_type="financial_report",
            period="2024-Q4",
            source_filename="report.txt",
            storage_path="Globex/financial_report/2024-Q4/2.txt",
            status="ready",
        )
        db.add_all([document, other_document])
        db.commit()
        db.refresh(document)
        db.refresh(other_document)

        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    page_number=1,
                    text="alpha",
                    token_count=1,
                    embedding=_make_embedding(1.0, 0.0),
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=1,
                    page_number=1,
                    text="alpha beta",
                    token_count=2,
                    embedding=_make_embedding(0.8, 0.2),
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=2,
                    page_number=2,
                    text="beta",
                    token_count=1,
                    embedding=_make_embedding(0.0, 1.0),
                ),
                DocumentChunk(
                    document_id=other_document.id,
                    chunk_index=0,
                    page_number=1,
                    text="other doc",
                    token_count=2,
                    embedding=_make_embedding(1.0, 0.0),
                ),
            ]
        )
        db.commit()

        return document.id, other_document.id
    finally:
        db.close()


def _retrieve(document_id: int, payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                f"/documents/{document_id}/retrieve",
                json=payload,
            )

    return asyncio.run(request())


def test_retrieve_endpoint_returns_ranked_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, _ = _seed_document_with_chunks()
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _retrieve(
        document_id,
        {
            "question": "alpha performance",
            "top_k": 2,
            "min_similarity": 0.5,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["document_id"] == document_id
    assert payload["question"] == "alpha performance"
    assert payload["top_k"] == 2
    assert payload["min_similarity"] == 0.5
    assert payload["result_count"] == 2
    assert [chunk["chunk_index"] for chunk in payload["chunks"]] == [0, 1]
    assert payload["chunks"][0]["similarity"] >= payload["chunks"][1]["similarity"]


def test_retrieve_endpoint_returns_404_for_missing_document() -> None:
    response = _retrieve(
        999,
        {
            "question": "alpha performance",
        },
    )

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_retrieve_endpoint_returns_400_for_invalid_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, _ = _seed_document_with_chunks()
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _retrieve(
        document_id,
        {
            "question": "   ",
        },
    )

    assert response.status_code == 400
    assert "question must not be empty" in response.json()["detail"]
