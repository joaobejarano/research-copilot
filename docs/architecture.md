# Stage 8 Architecture Additions

This document describes only what Stage 8 adds.

## Scope Added in Stage 8

- separate MCP server process in `mcp_server/`
- shared MCP configuration for server runtime and backend integration
- Stage 8 MCP tools for document discovery, chunk inspection, and document-scoped workflow actions
- structured MCP error payloads for predictable client-side handling

Out of scope in Stage 8:

- multi-step agent orchestration through MCP
- external MCP deployment infrastructure
- Stage 9+ MCP capability expansion

## Components Added in Stage 8

### MCP server bootstrap (`mcp_server/`)

- `mcp_server/config.py`
  - loads MCP-specific env vars
  - validates transport and port
  - resolves backend base URL and optional DB linkage
- `mcp_server/server.py`
  - creates `FastMCP` instance
  - registers tools/resources
- `mcp_server/main.py`
  - local entrypoint (`python -m mcp_server`)

### MCP tools

- `mcp_server/tools/documents.py`
  - `search_documents` (read-only metadata listing/filtering)
  - `fetch_document_chunks` (read-only chunk metadata/text)
- `mcp_server/tools/workflows.py`
  - `ask_document`
  - `generate_memo`
  - `extract_risks`
  - all document-scoped, routed through existing backend workflows
- `mcp_server/tools/errors.py`
  - structured MCP error model with:
    - `code`
    - `message`
    - `retryable`
    - `details`

### MCP resources

- `mcp_server/resources/`
  - registration placeholder kept explicit
  - no Stage 8 resource payloads added yet

## Stage 8 Runtime Flow

1. MCP server starts with validated MCP settings.
2. Client invokes an MCP tool.
3. Tool validates input and calls backend endpoint through `MCP_BACKEND_BASE_URL`.
4. MCP returns structured output aligned with backend contracts.
5. If failure occurs, MCP returns structured error payload with explicit error code.

## Stage 8 Design Constraints Enforced

- MCP stays separate from FastAPI backend process.
- Tools reuse existing backend behavior instead of duplicating business logic.
- Initial toolset is document-scoped only.
- Read-only inspection tools are preserved alongside first action tools.
- `insufficient_evidence` behavior from grounded workflows is preserved in MCP outputs.

## Stage 8 Test Coverage Added

- MCP server startup and tool registration tests
- schema/description inspection tests for exposed tools
- deterministic tool execution tests for:
  - `search_documents`
  - `fetch_document_chunks`
  - `ask_document`
  - `generate_memo`
  - `extract_risks`
- structured error-path tests for invalid input and backend failure mapping
