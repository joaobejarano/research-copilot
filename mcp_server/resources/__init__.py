from mcp.server.fastmcp import FastMCP

from mcp_server.config import MCPServerSettings


def register_resources(*, server: FastMCP, settings: MCPServerSettings) -> None:
    """Register MCP resources (Stage 8 foundation).

    Intentionally empty in Stage 8 bootstrap. Resource implementations will be added in later stages.
    """
    del server, settings
