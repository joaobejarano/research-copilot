import asyncio

from mcp_server.config import MCPServerSettings
from mcp_server.server import create_mcp_server


def test_create_mcp_server_bootstrap_registers_stage8_tools() -> None:
    settings = MCPServerSettings(
        server_name="Research Copilot MCP Test",
        transport="stdio",
        backend_base_url="http://127.0.0.1:8000",
        database_url="sqlite+pysqlite:////tmp/research-copilot-mcp-test.db",
        host="127.0.0.1",
        port=8811,
        mount_path="/",
    )

    server = create_mcp_server(settings)

    assert server.name == "Research Copilot MCP Test"
    assert server.settings.host == "127.0.0.1"
    assert server.settings.port == 8811
    assert server.settings.mount_path == "/"
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}
    assert tool_names == {
        "search_documents",
        "fetch_document_chunks",
        "ask_document",
        "generate_memo",
        "extract_risks",
    }

    tools_by_name = {tool.name: tool for tool in tools}
    ask_tool = tools_by_name["ask_document"]
    assert "insufficient_evidence" in (ask_tool.description or "")
    assert {"document_id", "question"} <= set(ask_tool.inputSchema["properties"])
    assert "must be >= 1" in ask_tool.inputSchema["properties"]["document_id"]["description"]
    assert set(ask_tool.outputSchema["properties"]["status"]["enum"]) == {
        "answered",
        "insufficient_evidence",
    }

    memo_tool = tools_by_name["generate_memo"]
    assert set(memo_tool.outputSchema["properties"]["status"]["enum"]) == {
        "generated",
        "insufficient_evidence",
    }

    risks_tool = tools_by_name["extract_risks"]
    assert set(risks_tool.outputSchema["properties"]["status"]["enum"]) == {
        "completed",
        "insufficient_evidence",
    }

    assert asyncio.run(server.list_resources()) == []
    assert asyncio.run(server.list_resource_templates()) == []
