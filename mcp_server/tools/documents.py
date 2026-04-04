from __future__ import annotations

from typing import Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config import MCPServerSettings

MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


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
    company_name_contains: str | None = Field(default=None, max_length=255)
    document_type: str | None = Field(default=None, max_length=100)
    period: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    limit: int = Field(default=50, ge=1, le=500)

    model_config = MODEL_CONFIG


class SearchDocumentsToolOutput(BaseModel):
    tool: Literal["search_documents"] = "search_documents"
    filters: SearchDocumentsFilters
    total_documents: int = Field(ge=0)
    returned_documents: int = Field(ge=0)
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
    status: str = Field(min_length=1, max_length=50)
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

    text = response.text.strip()
    return text or response.reason_phrase


def _request_backend_json(*, base_url: str, path: str) -> dict[str, Any] | list[Any]:
    response = httpx.get(f"{base_url}{path}", timeout=20.0)
    if response.status_code >= 400:
        detail = _extract_error_detail(response)
        raise ValueError(f"Backend request failed ({response.status_code}) for {path}: {detail}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"Backend response for {path} is not valid JSON.") from exc

    if not isinstance(payload, (dict, list)):
        raise ValueError(f"Backend response for {path} must be a JSON object or array.")

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
        raise ValueError("limit must be between 1 and 500.")

    payload = _request_backend_json(base_url=settings.backend_base_url, path="/documents")
    if not isinstance(payload, list):
        raise ValueError("Backend /documents response must be a JSON array.")

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
        raise ValueError("document_id must be >= 1.")

    payload = _request_backend_json(
        base_url=settings.backend_base_url,
        path=f"/documents/{document_id}/chunks",
    )
    if not isinstance(payload, dict):
        raise ValueError("Backend /documents/{document_id}/chunks response must be a JSON object.")

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
            "List documents from the backend with optional metadata filters. "
            "Read-only, document metadata only."
        ),
        structured_output=True,
    )
    def search_documents(
        company_name_contains: str | None = None,
        document_type: str | None = None,
        period: str | None = None,
        status: str | None = None,
        limit: int = 50,
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
            "Fetch chunk metadata and text for one document_id. "
            "Read-only; does not include raw embeddings."
        ),
        structured_output=True,
    )
    def fetch_document_chunks(document_id: int) -> FetchDocumentChunksToolOutput:
        return fetch_document_chunks_from_backend(settings=settings, document_id=document_id)
