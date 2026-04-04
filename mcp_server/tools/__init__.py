from mcp.server.fastmcp import FastMCP

from mcp_server.config import MCPServerSettings


def register_tools(*, server: FastMCP, settings: MCPServerSettings) -> None:
    """Register MCP tools (Stage 8 foundation).

    Intentionally empty in Stage 8 bootstrap. Tool implementations will be added in later stages.
    """
    del server, settings
