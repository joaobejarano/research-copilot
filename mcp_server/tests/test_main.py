from mcp_server.config import MCPServerSettings
from mcp_server import main as main_module


class _FakeServer:
    def __init__(self) -> None:
        self.received_transport: str | None = None

    def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
        del mount_path
        self.received_transport = transport


def test_main_runs_server_with_configured_transport(monkeypatch) -> None:
    settings = MCPServerSettings(
        server_name="Research Copilot MCP Test",
        transport="sse",
        backend_base_url="http://127.0.0.1:8000",
        database_url=None,
        host="127.0.0.1",
        port=8811,
        mount_path="/",
    )
    fake_server = _FakeServer()

    monkeypatch.setattr(main_module, "load_mcp_server_settings", lambda: settings)
    monkeypatch.setattr(main_module, "create_mcp_server", lambda _: fake_server)

    assert main_module.main() == 0
    assert fake_server.received_transport == "sse"
