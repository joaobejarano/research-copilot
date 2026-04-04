from __future__ import annotations

from typing import Annotated, Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config import MCPServerSettings
from mcp_server.tools.errors import raise_mcp_tool_error

MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)

DocumentIdParam = Annotated[
    int,
    Field(description="Document identifier from the Research Copilot backend (must be >= 1)."),
]


class DocumentMetadata(BaseModel):
    id: int = Field(ge=1)
    company_name: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=100)
    period: str = Field(min_length=1, max_length=50)
    source_filename: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=500)
    status: str = Field(min_length=1, max_length=50)
    created_at: str = Field(min_length=1, max_length=80)

    model_config = MODEL_CONFIG


class SearchDocumentsFilters(BaseModel):
    company_name_contains: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive company-name substring filter.",
    )
    document_type: str | None = Field(
        default=None,
        max_length=100,
        description="Exact document_type filter.",
    )
    period: str | None = Field(
        default=None,
        max_length=50,
        description="Exact reporting period filter.",
    )
    status: str | None = Field(
        default=None,
        max_length=50,
        description="Exact backend document status filter.",
    )
    limit: int = Field(default=50, ge=1, le=500, description="Maximum number of rows returned.")

    model_config = MODEL_CONFIG


class SearchDocumentsToolOutput(BaseModel):
    tool: Literal["search_documents"] = "search_documents"
    filters: SearchDocumentsFilters = Field(description="Effective filters applied by the tool.")
    total_documents: int = Field(ge=0, description="Total documents available before filtering.")
    returned_documents: int = Field(ge=0, description="Number of documents returned after filtering.")
    documents: list[DocumentMetadata] = Field(default_factory=list, max_length=500)

    model_config = MODEL_CONFIG


class DocumentChunkSummary(BaseModel):
    chunk_index: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1)
    token_count: int = Field(ge=0)

    model_config = MODEL_CONFIG


class FetchDocumentChunksToolOutput(BaseModel):
    tool: Literal["fetch_document_chunks"] = "fetch_document_chunks"
    document_id: int = Field(ge=1)
    status: str = Field(
        min_length=1,
        max_length=50,
        description="Current backend document status.",
    )
    chunk_count: int = Field(ge=0)
    embedding_dimension: int = Field(ge=0)
    chunks: list[DocumentChunkSummary] = Field(default_factory=list, max_length=5000)

    model_config = MODEL_CONFIG


class _BackendDocumentChunksResponse(BaseModel):
    document_id: int = Field(ge=1)
    status: str = Field(min_length=1, max_length=50)
    chunk_count: int = Field(ge=0)
    embedding_dimension: int = Field(ge=0)
    chunks: list[DocumentChunkSummary] = Field(default_factory=list, max_length=5000)

    model_config = MODEL_CONFIG


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
        if isinstance(detail, list):
            return "Request validation failed."

    text = response.text.strip()
    return text or response.reason_phrase


def _raise_backend_http_error(*, response: httpx.Response, method: str, path: str) -> None:
    detail = _extract_error_detail(response)
    lowered_detail = detail.lower()

    if response.status_code == 404 and "document not found" in lowered_detail:
        raise_mcp_tool_error(
            code="document_not_found",
            message="Document was not found.",
            details={"method": method, "path": path, "status_code": response.status_code},
        )

    if response.status_code == 400 and "must be processed and ready" in lowered_detail:
        raise_mcp_tool_error(
            code="document_not_ready",
            message="Document must be processed and ready before running this workflow.",
            details={"method": method, "path": path, "status_code": response.status_code},
        )

    raise_mcp_tool_error(
        code="backend_request_failed",
        message=detail or "Backend rejected the MCP request.",
        details={"method": method, "path": path, "status_code": response.status_code},
    )


def _request_backend_json(
    *,
    base_url: str,
    path: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    request_kwargs: dict[str, Any] = {
        "method": method,
        "url": f"{base_url}{path}",
        "timeout": 20.0,
    }
    if body is not None:
        request_kwargs["json"] = body

    try:
        response = httpx.request(**request_kwargs)
    except httpx.RequestError:
        raise_mcp_tool_error(
            code="backend_unreachable",
            message="Could not reach backend service.",
            retryable=True,
            details={"method": method, "path": path},
        )

    if response.status_code >= 400:
        _raise_backend_http_error(response=response, method=method, path=path)

    try:
        payload = response.json()
    except ValueError:
        raise_mcp_tool_error(
            code="backend_invalid_response",
            message="Backend returned non-JSON data.",
            details={"method": method, "path": path},
        )

    if not isinstance(payload, (dict, list)):
        raise_mcp_tool_error(
            code="backend_invalid_response",
            message="Backend response must be a JSON object or array.",
            details={"method": method, "path": path},
        )

    return payload


def search_documents_from_backend(
    *,
    settings: MCPServerSettings,
    company_name_contains: str | None = None,
    document_type: str | None = None,
    period: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> SearchDocumentsToolOutput:
    if limit < 1 or limit > 500:
        raise_mcp_tool_error(
            code="invalid_limit",
            message="limit must be between 1 and 500.",
            details={"limit": limit},
        )

    payload = _request_backend_json(base_url=settings.backend_base_url, path="/documents")
    if not isinstance(payload, list):
        raise_mcp_tool_error(
            code="backend_invalid_response",
            message="Backend /documents response must be a JSON array.",
            details={"method": "GET", "path": "/documents"},
        )

    documents = [DocumentMetadata.model_validate(item) for item in payload]

    normalized_company_name_contains = _normalize_filter(company_name_contains)
    normalized_document_type = _normalize_filter(document_type)
    normalized_period = _normalize_filter(period)
    normalized_status = _normalize_filter(status)

    filtered_documents = documents

    if normalized_company_name_contains is not None:
        needle = normalized_company_name_contains.lower()
        filtered_documents = [
            document
            for document in filtered_documents
            if needle in document.company_name.lower()
        ]

    if normalized_document_type is not None:
        filtered_documents = [
            document
            for document in filtered_documents
            if document.document_type == normalized_document_type
        ]

    if normalized_period is not None:
        filtered_documents = [
            document for document in filtered_documents if document.period == normalized_period
        ]

    if normalized_status is not None:
        filtered_documents = [
            document for document in filtered_documents if document.status == normalized_status
        ]

    limited_documents = filtered_documents[:limit]

    return SearchDocumentsToolOutput(
        filters=SearchDocumentsFilters(
            company_name_contains=normalized_company_name_contains,
            document_type=normalized_document_type,
            period=normalized_period,
            status=normalized_status,
            limit=limit,
        ),
        total_documents=len(documents),
        returned_documents=len(limited_documents),
        documents=limited_documents,
    )


def fetch_document_chunks_from_backend(
    *,
    settings: MCPServerSettings,
    document_id: int,
) -> FetchDocumentChunksToolOutput:
    if document_id < 1:
        raise_mcp_tool_error(
            code="invalid_document_id",
            message="document_id must be >= 1.",
            details={"document_id": document_id},
        )

    payload = _request_backend_json(
        base_url=settings.backend_base_url,
        path=f"/documents/{document_id}/chunks",
    )
    if not isinstance(payload, dict):
        raise_mcp_tool_error(
            code="backend_invalid_response",
            message="Backend /documents/{document_id}/chunks response must be a JSON object.",
            details={"method": "GET", "path": f"/documents/{document_id}/chunks"},
        )

    chunks_response = _BackendDocumentChunksResponse.model_validate(payload)

    return FetchDocumentChunksToolOutput(
        document_id=chunks_response.document_id,
        status=chunks_response.status,
        chunk_count=chunks_response.chunk_count,
        embedding_dimension=chunks_response.embedding_dimension,
        chunks=chunks_response.chunks,
    )


def register_document_tools(*, server: FastMCP, settings: MCPServerSettings) -> None:
    @server.tool(
        name="search_documents",
        description=(
            "Read-only document discovery. Use optional metadata filters and receive "
            "a structured list of matching documents with applied filters and counts."
        ),
        structured_output=True,
    )
    def search_documents(
        company_name_contains: Annotated[
            str | None,
            Field(
                max_length=255,
                description="Optional company-name substring filter (case-insensitive).",
            ),
        ] = None,
        document_type: Annotated[
            str | None,
            Field(max_length=100, description="Optional exact document_type filter."),
        ] = None,
        period: Annotated[
            str | None,
            Field(max_length=50, description="Optional exact period filter."),
        ] = None,
        status: Annotated[
            str | None,
            Field(max_length=50, description="Optional exact backend status filter."),
        ] = None,
        limit: Annotated[
            int,
            Field(ge=1, le=500, description="Maximum rows to return."),
        ] = 50,
    ) -> SearchDocumentsToolOutput:
        return search_documents_from_backend(
            settings=settings,
            company_name_contains=company_name_contains,
            document_type=document_type,
            period=period,
            status=status,
            limit=limit,
        )

    @server.tool(
        name="fetch_document_chunks",
        description=(
            "Read-only chunk inspection for a single document_id. Returns chunk metadata "
            "and chunk text only; raw embeddings are never returned."
        ),
        structured_output=True,
    )
    def fetch_document_chunks(document_id: DocumentIdParam) -> FetchDocumentChunksToolOutput:
        return fetch_document_chunks_from_backend(settings=settings, document_id=document_id)
