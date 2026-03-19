import asyncio

import httpx

from app.main import app

METADATA_KEYS = {
    "id",
    "company_name",
    "document_type",
    "period",
    "source_filename",
    "storage_path",
    "status",
    "created_at",
}


def _upload_document(
    *,
    company_name: str,
    document_type: str,
    period: str,
    filename: str,
    content: bytes,
    content_type: str,
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
                    "company_name": company_name,
                    "document_type": document_type,
                    "period": period,
                },
                files={"file": (filename, content, content_type)},
            )

    response = asyncio.run(request_upload())
    assert response.status_code == 201
    return response.json()


def test_list_documents_returns_uploaded_metadata() -> None:
    first_document = _upload_document(
        company_name="Acme Corp",
        document_type="financial_report",
        period="2024-Q4",
        filename="report.pdf",
        content=b"sample report",
        content_type="application/pdf",
    )
    second_document = _upload_document(
        company_name="Globex",
        document_type="meeting_notes",
        period="2025-01",
        filename="notes.txt",
        content=b"sample notes",
        content_type="text/plain",
    )

    async def request_documents() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/documents")

    response = asyncio.run(request_documents())

    assert response.status_code == 200
    payload = response.json()

    assert len(payload) == 2
    assert [item["id"] for item in payload] == [first_document["id"], second_document["id"]]
    assert set(payload[0].keys()) == METADATA_KEYS
    assert set(payload[1].keys()) == METADATA_KEYS
    assert payload[0]["source_filename"] == "report.pdf"
    assert payload[1]["source_filename"] == "notes.txt"
    assert payload[0]["storage_path"].endswith(f"{first_document['id']}.pdf")
    assert payload[1]["storage_path"].endswith(f"{second_document['id']}.txt")


def test_get_document_returns_metadata() -> None:
    uploaded_document = _upload_document(
        company_name="Acme Corp",
        document_type="financial_report",
        period="2024-Q4",
        filename="report.docx",
        content=b"sample report",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    async def request_document(document_id: int) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(f"/documents/{document_id}")

    response = asyncio.run(request_document(uploaded_document["id"]))

    assert response.status_code == 200
    payload = response.json()

    assert set(payload.keys()) == METADATA_KEYS
    assert payload["id"] == uploaded_document["id"]
    assert payload["company_name"] == "Acme Corp"
    assert payload["source_filename"] == "report.docx"
    assert payload["storage_path"].endswith(f"{uploaded_document['id']}.docx")
    assert payload["status"] == "uploaded"


def test_get_document_returns_404_when_not_found() -> None:
    async def request_document() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/documents/999")

    response = asyncio.run(request_document())

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}
