from mcp.server.fastmcp import FastMCP

from mcp_server.config import MCPServerSettings, load_mcp_server_settings
from mcp_server.resources import register_resources
from mcp_server.tools import register_tools


def create_mcp_server(settings: MCPServerSettings | None = None) -> FastMCP:
    resolved_settings = settings or load_mcp_server_settings()

    server = FastMCP(
        name=resolved_settings.server_name,
        instructions=(
            "Research Copilot MCP server bootstrap. "
            "Stage 8 foundation with configuration and registration structure only."
        ),
        host=resolved_settings.host,
        port=resolved_settings.port,
        mount_path=resolved_settings.mount_path,
    )

    register_tools(server=server, settings=resolved_settings)
    register_resources(server=server, settings=resolved_settings)

    return server
