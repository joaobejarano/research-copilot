import asyncio

import httpx
import pytest

from app.api.routes import documents as documents_routes
from app.core.config import EMBEDDING_DIMENSION
from app.db.database import SessionLocal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.main import app
from app.qa.service import Citation, QuestionAnswerResult
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


def _seed_document_with_chunk(*, text: str) -> tuple[int, int]:
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
            text=text,
            token_count=10,
            embedding=_make_embedding(1.0, 0.0),
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return document.id, chunk.chunk_index
    finally:
        db.close()


def _verify_ask(document_id: int, payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(f"/documents/{document_id}/verify/ask", json=payload)

    return asyncio.run(request())


def test_verify_ask_endpoint_returns_verification_and_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, _ = _seed_document_with_chunk(
        text=(
            "Revenue increased 12 percent in Q4 due to subscription expansion "
            "and improved enterprise renewals."
        )
    )
    monkeypatch.setattr(
        retrieval_service,
        "get_embedding_provider",
        lambda: FakeEmbeddingProvider(_make_embedding(1.0, 0.0)),
    )

    response = _verify_ask(
        document_id,
        {"question": "What happened to revenue in Q4?", "top_k": 3, "min_similarity": 0.2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "What happened to revenue in Q4?"
    assert payload["status"] == "answered"
    assert "verification" in payload
    assert "confidence" in payload
    assert "gate_decision" in payload
    assert "issues" in payload
    assert isinstance(payload["issues"], list)

    verification = payload["verification"]
    assert verification["status"] in {"passed", "inconclusive"}
    check_names = {check["check_name"] for check in verification["checks"]}
    assert check_names == {
        "citation_exists",
        "citation_document_match",
        "citation_excerpt_in_chunk",
    }

    confidence = payload["confidence"]
    signal_names = {signal["signal_name"] for signal in confidence["signals"]}
    assert signal_names == {
        "supporting_citation_count",
        "retrieval_score_quality",
        "verification_outcome",
        "unsupported_numeric_claims",
    }


def test_verify_ask_endpoint_detects_unsupported_numeric_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, chunk_index = _seed_document_with_chunk(
        text="Revenue was 120 in Q4 and operating margin held steady."
    )

    monkeypatch.setattr(
        documents_routes,
        "answer_document_question",
        lambda **kwargs: QuestionAnswerResult(
            question="What was revenue?",
            answer="Revenue was 999 in Q4. [C1]",
            status="answered",
            citations=[
                Citation(
                    citation_id="C1",
                    rank=1,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    page_number=1,
                    text_excerpt="Revenue was 120 in Q4 and operating margin held steady.",
                    retrieval_score=0.9,
                )
            ],
        ),
    )

    response = _verify_ask(document_id, {"question": "What was revenue?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"]["status"] == "passed"
    assert any(
        "Unsupported numeric claims detected" in issue for issue in payload["issues"]
    )
    numeric_signal = next(
        signal
        for signal in payload["confidence"]["signals"]
        if signal["signal_name"] == "unsupported_numeric_claims"
    )
    assert numeric_signal["value"] == 0.0


def test_verify_ask_endpoint_returns_404_for_missing_document() -> None:
    response = _verify_ask(999, {"question": "What happened to revenue?"})

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]
