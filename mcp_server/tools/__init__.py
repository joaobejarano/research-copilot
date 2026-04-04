from mcp.server.fastmcp import FastMCP

from mcp_server.config import MCPServerSettings
from mcp_server.tools.documents import register_document_tools
from mcp_server.tools.workflows import register_workflow_tools


def register_tools(*, server: FastMCP, settings: MCPServerSettings) -> None:
    register_document_tools(server=server, settings=settings)
    register_workflow_tools(server=server, settings=settings)
