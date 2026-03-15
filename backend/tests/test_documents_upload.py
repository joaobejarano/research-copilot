import asyncio
import os
from pathlib import Path

import httpx

from app.main import app


def test_upload_document() -> None:
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
                files={"file": ("report.pdf", b"sample content", "application/pdf")},
            )

    response = asyncio.run(request_upload())

    assert response.status_code == 201
    payload = response.json()

    assert isinstance(payload["id"], int)
    assert payload["company_name"] == "Acme Corp"
    assert payload["document_type"] == "financial_report"
    assert payload["period"] == "2024-Q4"
    assert payload["source_filename"] == "report.pdf"
    assert payload["status"] == "uploaded"
    assert payload["created_at"]

    storage_path = (
        Path(os.environ["STORAGE_DIR"])
        / "Acme_Corp"
        / "financial_report"
        / "2024-Q4"
        / f"{payload['id']}.pdf"
    )
    assert storage_path.exists()
    assert storage_path.read_bytes() == b"sample content"


def test_upload_rejects_unsupported_extension() -> None:
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
                files={
                    "file": ("report.exe", b"sample content", "application/octet-stream")
                },
            )

    response = asyncio.run(request_upload())

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]
