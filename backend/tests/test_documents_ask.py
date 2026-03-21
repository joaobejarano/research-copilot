import asyncio

import httpx
import pytest

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.main import app
from app.retrieval import service as retrieval_service

CITATION_KEYS = {
    "citation_id",
    "rank",
    "document_id",
    "chunk_index",
    "page_number",
    "text_excerpt",
    "retrieval_score",
}


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


def _seed_document_with_chunks(
    *,
    status: str,
    chunk_specs: list[tuple[int, int | None, str, int, list[float]]],
) -> int:
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

        for chunk_index, page_number, text, token_count, embedding in chunk_specs:
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    text=text,
                    token_count=token_count,
                    embedding=embedding,
                )
            )
        db.commit()
        return document.id
    finally:
        db.close()


def _ask(document_id: int, payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(f"/documents/{document_id}/ask", json=payload)

    return asyncio.run(request())


def _assert_citation_payload(
    citation: dict[str, object],
    *,
    expected_citation_id: str,
    expected_rank: int,
    expected_document_id: int,
) -> None:
    assert set(citation.keys()) == CITATION_KEYS
    assert citation["citation_id"] == expected_citation_id
    assert citation["rank"] == expected_rank
    assert citation["document_id"] == expected_document_id
    assert isinstance(citation["chunk_index"], int)
    assert citation["page_number"] is None or isinstance(citation["page_number"], int)
    assert isinstance(citation["text_excerpt"], str)
    assert citation["text_excerpt"]
    assert len(citation["text_excerpt"]) <= 180
    assert isinstance(citation["retrieval_score"], float)


def test_ask_endpoint_returns_grounded_answer_with_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_sentence = (
        "Revenue increased 12 percent in Q4 due to subscription expansion in enterprise "
        "accounts and stronger renewal rates across strategic segments with predictable "
        "seasonal demand and disciplined pricing execution."
    )
    document_id = _seed_document_with_chunks(
        status="ready",
        chunk_specs=[
            (
                0,
                1,
                f"{long_sentence} Gross margin remained stable.",
                31,
                _make_embedding(1.0, 0.0),
            ),
            (
                1,
                2,
                "Operating costs decreased by 5 percent year over year.",
                9,
                _make_embedding(0.8, 0.2),
            ),
        ],
    )
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _ask(
        document_id,
        {"question": "What happened to revenue in Q4?", "top_k": 3, "min_similarity": 0.2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["question"] == "What happened to revenue in Q4?"
    assert "Revenue increased 12 percent in Q4" in payload["answer"]
    citations = payload["citations"]
    assert len(citations) >= 1
    assert [item["citation_id"] for item in citations] == [
        f"C{index}" for index in range(1, len(citations) + 1)
    ]
    for rank, citation in enumerate(citations, start=1):
        _assert_citation_payload(
            citation,
            expected_citation_id=f"C{rank}",
            expected_rank=rank,
            expected_document_id=document_id,
        )
        assert f"[C{rank}]" in payload["answer"]
    assert citations[0]["chunk_index"] == 0
    assert citations[0]["page_number"] == 1
    assert "Revenue increased" in citations[0]["text_excerpt"]
    assert str(citations[0]["text_excerpt"]).endswith("...")


def test_ask_endpoint_returns_insufficient_evidence_when_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document_with_chunks(
        status="ready",
        chunk_specs=[
            (0, 1, "Cash flow remained consistent.", 4, _make_embedding(0.0, 1.0)),
        ],
    )
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _ask(
        document_id,
        {
            "question": "What happened to revenue?",
            "top_k": 3,
            "min_similarity": 0.95,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_evidence"
    assert payload["citations"] == []
    assert "Insufficient evidence" in payload["answer"]


def test_ask_endpoint_returns_insufficient_evidence_for_weak_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document_with_chunks(
        status="ready",
        chunk_specs=[
            (0, 1, "Revenue increased 12 percent in Q4.", 6, _make_embedding(1.0, 0.0)),
        ],
    )
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _ask(
        document_id,
        {"question": "What debt covenant breaches were reported?", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_evidence"
    assert len(payload["citations"]) == 1
    _assert_citation_payload(
        payload["citations"][0],
        expected_citation_id="C1",
        expected_rank=1,
        expected_document_id=document_id,
    )
    assert payload["citations"][0]["chunk_index"] == 0
    assert "Insufficient evidence" in payload["answer"]


def test_ask_endpoint_limits_citations_to_top_three_for_insufficient_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _seed_document_with_chunks(
        status="ready",
        chunk_specs=[
            (0, 1, "Revenue increased in Q4.", 4, _make_embedding(1.0, 0.0)),
            (1, 1, "Operating margin remained stable.", 4, _make_embedding(1.0, 0.0)),
            (2, 2, "Cash flow stayed predictable.", 4, _make_embedding(1.0, 0.0)),
            (3, 2, "Headcount grew in core teams.", 5, _make_embedding(1.0, 0.0)),
        ],
    )
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _ask(
        document_id,
        {
            "question": "What debt covenant breaches were reported?",
            "top_k": 5,
            "min_similarity": 0.1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_evidence"
    assert "Insufficient evidence" in payload["answer"]
    assert len(payload["citations"]) == 3
    assert [item["citation_id"] for item in payload["citations"]] == ["C1", "C2", "C3"]
    assert [item["chunk_index"] for item in payload["citations"]] == [0, 1, 2]
    for rank, citation in enumerate(payload["citations"], start=1):
        _assert_citation_payload(
            citation,
            expected_citation_id=f"C{rank}",
            expected_rank=rank,
            expected_document_id=document_id,
        )


def test_ask_endpoint_returns_404_for_missing_document() -> None:
    response = _ask(999, {"question": "What happened to revenue?"})

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]
