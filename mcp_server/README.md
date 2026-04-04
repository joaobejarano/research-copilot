# MCP Server (Stage 8 Foundation)

This package is a separate FastMCP server bootstrap, intentionally isolated from `backend/`.

## Structure

- `mcp_server/config.py`: MCP-specific environment and integration settings
- `mcp_server/server.py`: FastMCP bootstrap + registration entry points
- `mcp_server/main.py`: runtime entry point (`python -m mcp_server`)
- `mcp_server/tools/`: tool registration and read-only document tools
- `mcp_server/resources/`: placeholder resource registry (no resources yet)

## Tools (Stage 8)

- `search_documents`
  - returns backend document metadata list
  - supports optional metadata filtering (`company_name_contains`, `document_type`, `period`, `status`, `limit`)
- `fetch_document_chunks`
  - requires `document_id`
  - returns chunk metadata and text
  - does not return raw embeddings

## Run locally

```bash
python -m mcp_server
```

Control transport with `MCP_TRANSPORT`:

- `stdio` (default)
- `sse`
- `streamable-http`
