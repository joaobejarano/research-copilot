# MCP Server (Stage 8 Foundation)

This package is a separate FastMCP server bootstrap, intentionally isolated from `backend/`.

## Structure

- `mcp_server/config.py`: MCP-specific environment and integration settings
- `mcp_server/server.py`: FastMCP bootstrap + registration entry points
- `mcp_server/main.py`: runtime entry point (`python -m mcp_server`)
- `mcp_server/tools/`: placeholder tool registry (no tools yet)
- `mcp_server/resources/`: placeholder resource registry (no resources yet)

## Run locally

```bash
python -m mcp_server
```

Control transport with `MCP_TRANSPORT`:

- `stdio` (default)
- `sse`
- `streamable-http`
