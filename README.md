# Research Copilot

Research Copilot is in Stage 8.

Stage 8 adds a separate MCP server that exposes document-scoped tools backed by existing FastAPI workflows.

## Stage 8: MCP Server

### How Stage 8 MCP works

- MCP runs as a separate process in `mcp_server/`.
- The MCP server calls existing backend endpoints through `MCP_BACKEND_BASE_URL`.
- Tool outputs are structured and aligned to backend response schemas.
- Action tools preserve grounded behavior, including `insufficient_evidence`.
- Errors are returned as structured payloads (`code`, `message`, `retryable`, `details`) for client inspection.

### Required environment variables

Minimum MCP settings:

- `MCP_SERVER_NAME` (default: `Research Copilot MCP`)
- `MCP_TRANSPORT` (`stdio`, `sse`, or `streamable-http`; default: `stdio`)
- `MCP_BACKEND_BASE_URL` (default: `http://127.0.0.1:8000`)

Common local overrides:

- `MCP_SERVER_HOST` (default: `127.0.0.1`)
- `MCP_SERVER_PORT` (default: `8811`)
- `MCP_MOUNT_PATH` (default: `/`)
- `MCP_DATABASE_URL` (optional; falls back to `DATABASE_URL`)

Backend still requires its own runtime env (for example `DATABASE_URL`, `STORAGE_DIR`, and workflow/provider settings).

### How to start the MCP server locally

Start backend first:

```bash
cd backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Start MCP server from repo root:

```bash
python -m mcp_server
```

### Exposed MCP tools

Read-only tools:

- `search_documents`
- `fetch_document_chunks`

Action tools (document-scoped):

- `ask_document`
- `generate_memo`
- `extract_risks`

### How to validate MCP tools locally

Use in-process tool calls:

```bash
python - <<'PY'
import asyncio
from mcp_server.config import load_mcp_server_settings
from mcp_server.server import create_mcp_server

async def main():
    server = create_mcp_server(load_mcp_server_settings())

    print(await server.call_tool("search_documents", {"limit": 5}))
    print(await server.call_tool("fetch_document_chunks", {"document_id": 1}))
    print(await server.call_tool("ask_document", {"document_id": 1, "question": "What changed in revenue in Q4?"}))
    print(await server.call_tool("generate_memo", {"document_id": 1}))
    print(await server.call_tool("extract_risks", {"document_id": 1}))

asyncio.run(main())
PY
```

Expected behavior:

- ready, grounded answers return normal structured payloads
- low evidence paths return `insufficient_evidence` status in action tool outputs
- invalid inputs/backend failures return structured MCP tool errors

### How to run tests

MCP server tests:

```bash
.venv/bin/pytest -q mcp_server/tests
```

Optional broader backend tests:

```bash
pytest -q backend/tests
```
