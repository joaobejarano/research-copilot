import asyncio

import httpx
import pytest

from app.api.routes import documents as documents_routes
from app.db.models.document import Document
from app.main import app


def _upload_document(
    *,
    filename: str = "report.txt",
    content: bytes = b"alpha beta gamma delta",
    content_type: str = "text/plain",
) -> dict[str, str | int]:
    async def request_upload() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/documents/upload",
                data={
                    "company_name": "Acme Corp",
                    "document_type": "financial_report",
                    "period": "2024-Q4",
                },
                files={"file": (filename, content, content_type)},
            )

    response = asyncio.run(request_upload())
    assert response.status_code == 201
    return response.json()


def _process_document(document_id: int) -> httpx.Response:
    async def request_processing() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(f"/documents/{document_id}/process")

    return asyncio.run(request_processing())


def _get_document(document_id: int) -> httpx.Response:
    async def request_document() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(f"/documents/{document_id}")

    return asyncio.run(request_document())


def test_process_document_updates_status_to_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_document = _upload_document()

    def fake_process_uploaded_document(*, db: object, document_id: int) -> int:
        assert document_id == uploaded_document["id"]
        current_document = db.get(Document, document_id)
        assert current_document is not None
        assert current_document.status == "processing"
        return 2

    monkeypatch.setattr(
        documents_routes,
        "process_uploaded_document",
        fake_process_uploaded_document,
    )

    response = _process_document(uploaded_document["id"])

    assert response.status_code == 200
    assert response.json() == {
        "document_id": uploaded_document["id"],
        "status": "ready",
        "chunk_count": 2,
    }

    document_response = _get_document(uploaded_document["id"])
    assert document_response.status_code == 200
    assert document_response.json()["status"] == "ready"


def test_process_document_updates_status_to_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_document = _upload_document()

    def fake_process_uploaded_document(*, db: object, document_id: int) -> int:
        raise ValueError("Unsupported document extension '.docx'.")

    monkeypatch.setattr(
        documents_routes,
        "process_uploaded_document",
        fake_process_uploaded_document,
    )

    response = _process_document(uploaded_document["id"])

    assert response.status_code == 400
    assert "Document processing failed" in response.json()["detail"]

    document_response = _get_document(uploaded_document["id"])
    assert document_response.status_code == 200
    assert document_response.json()["status"] == "failed"


def test_process_document_returns_404_for_missing_document() -> None:
    response = _process_document(999)

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}
