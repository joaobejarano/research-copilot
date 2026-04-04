import asyncio
from typing import Any

import pytest

from mcp_server.config import MCPServerSettings
from mcp_server.server import create_mcp_server
from mcp_server.tools import documents as document_tools


def _settings() -> MCPServerSettings:
    return MCPServerSettings(
        server_name="Research Copilot MCP Test",
        transport="stdio",
        backend_base_url="http://127.0.0.1:8000",
        database_url="sqlite+pysqlite:////tmp/research-copilot-mcp-test.db",
        host="127.0.0.1",
        port=8811,
        mount_path="/",
    )


def _extract_structured_tool_output(result: object) -> dict[str, Any]:
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
        return result[1]
    if isinstance(result, dict):
        return result
    raise AssertionError(f"Unexpected MCP call_tool result shape: {result!r}")


def test_search_documents_from_backend_filters_and_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [
        {
            "id": 1,
            "company_name": "Acme Corp",
            "document_type": "financial_report",
            "period": "2024-Q4",
            "source_filename": "acme_q4.txt",
            "storage_path": "Acme_Corp/financial_report/2024-Q4/1.txt",
            "status": "ready",
            "created_at": "2026-04-03T18:00:00Z",
        },
        {
            "id": 2,
            "company_name": "Acme Corp",
            "document_type": "financial_report",
            "period": "2025-Q1",
            "source_filename": "acme_q1.txt",
            "storage_path": "Acme_Corp/financial_report/2025-Q1/2.txt",
            "status": "uploaded",
            "created_at": "2026-04-03T18:01:00Z",
        },
        {
            "id": 3,
            "company_name": "Beta Holdings",
            "document_type": "earnings_call",
            "period": "2024-Q4",
            "source_filename": "beta_q4.txt",
            "storage_path": "Beta_Holdings/earnings_call/2024-Q4/3.txt",
            "status": "ready",
            "created_at": "2026-04-03T18:02:00Z",
        },
    ]

    monkeypatch.setattr(document_tools, "_request_backend_json", lambda **kwargs: payload)

    output = document_tools.search_documents_from_backend(
        settings=_settings(),
        company_name_contains="acme",
        status="ready",
        limit=5,
    )

    assert output.tool == "search_documents"
    assert output.total_documents == 3
    assert output.returned_documents == 1
    assert len(output.documents) == 1
    assert output.documents[0].id == 1
    assert output.filters.company_name_contains == "acme"
    assert output.filters.status == "ready"


def test_fetch_document_chunks_from_backend_returns_chunk_text_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "document_id": 9,
        "status": "ready",
        "chunk_count": 2,
        "embedding_dimension": 384,
        "chunks": [
            {
                "chunk_index": 0,
                "page_number": 1,
                "text": "Revenue increased 12 percent in Q4.",
                "token_count": 8,
            },
            {
                "chunk_index": 1,
                "page_number": 2,
                "text": "FX volatility remained a medium risk.",
                "token_count": 7,
            },
        ],
    }
    monkeypatch.setattr(document_tools, "_request_backend_json", lambda **kwargs: payload)

    output = document_tools.fetch_document_chunks_from_backend(settings=_settings(), document_id=9)
    dumped = output.model_dump()

    assert output.tool == "fetch_document_chunks"
    assert output.document_id == 9
    assert output.chunk_count == 2
    assert output.embedding_dimension == 384
    assert len(output.chunks) == 2
    assert output.chunks[0].text.startswith("Revenue")

    for chunk_payload in dumped["chunks"]:
        assert set(chunk_payload.keys()) == {
            "chunk_index",
            "page_number",
            "text",
            "token_count",
        }


def test_fetch_document_chunks_from_backend_rejects_invalid_document_id() -> None:
    with pytest.raises(ValueError, match="document_id"):
        document_tools.fetch_document_chunks_from_backend(settings=_settings(), document_id=0)


def test_registered_document_tools_can_be_invoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request_backend_json(*, base_url: str, path: str) -> dict[str, Any] | list[Any]:
        assert base_url == "http://127.0.0.1:8000"
        if path == "/documents":
            return [
                {
                    "id": 1,
                    "company_name": "Acme Corp",
                    "document_type": "financial_report",
                    "period": "2024-Q4",
                    "source_filename": "acme_q4.txt",
                    "storage_path": "Acme_Corp/financial_report/2024-Q4/1.txt",
                    "status": "ready",
                    "created_at": "2026-04-03T18:00:00Z",
                }
            ]
        if path == "/documents/1/chunks":
            return {
                "document_id": 1,
                "status": "ready",
                "chunk_count": 1,
                "embedding_dimension": 384,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "page_number": 1,
                        "text": "Revenue increased 12 percent in Q4.",
                        "token_count": 8,
                    }
                ],
            }
        raise AssertionError(f"Unexpected backend path: {path}")

    monkeypatch.setattr(document_tools, "_request_backend_json", fake_request_backend_json)

    server = create_mcp_server(_settings())

    search_result = asyncio.run(
        server.call_tool(
            "search_documents",
            {
                "company_name_contains": "Acme",
                "limit": 10,
            },
        )
    )
    search_payload = _extract_structured_tool_output(search_result)
    assert search_payload["tool"] == "search_documents"
    assert search_payload["returned_documents"] == 1
    assert search_payload["documents"][0]["company_name"] == "Acme Corp"

    chunks_result = asyncio.run(server.call_tool("fetch_document_chunks", {"document_id": 1}))
    chunks_payload = _extract_structured_tool_output(chunks_result)
    assert chunks_payload["tool"] == "fetch_document_chunks"
    assert chunks_payload["document_id"] == 1
    assert chunks_payload["chunks"][0]["text"].startswith("Revenue")
