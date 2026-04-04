import pytest

from mcp_server.config import load_mcp_server_settings


def _clear_mcp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MCP_SERVER_NAME",
        "MCP_TRANSPORT",
        "MCP_BACKEND_BASE_URL",
        "MCP_DATABASE_URL",
        "MCP_SERVER_HOST",
        "MCP_SERVER_PORT",
        "MCP_MOUNT_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


def test_load_mcp_server_settings_defaults_and_shared_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_mcp_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:////tmp/shared-stage8.db")

    settings = load_mcp_server_settings()

    assert settings.server_name == "Research Copilot MCP"
    assert settings.transport == "stdio"
    assert settings.backend_base_url == "http://127.0.0.1:8000"
    assert settings.database_url == "sqlite+pysqlite:////tmp/shared-stage8.db"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8811
    assert settings.mount_path == "/"


def test_load_mcp_server_settings_accepts_explicit_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_mcp_env(monkeypatch)
    monkeypatch.setenv("MCP_SERVER_NAME", "Research Copilot MCP Local")
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_BACKEND_BASE_URL", "http://localhost:9000/")
    monkeypatch.setenv("MCP_DATABASE_URL", "sqlite+pysqlite:////tmp/mcp-only.db")
    monkeypatch.setenv("MCP_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_SERVER_PORT", "9900")
    monkeypatch.setenv("MCP_MOUNT_PATH", "/mcp")

    settings = load_mcp_server_settings()

    assert settings.server_name == "Research Copilot MCP Local"
    assert settings.transport == "streamable-http"
    assert settings.backend_base_url == "http://localhost:9000"
    assert settings.database_url == "sqlite+pysqlite:////tmp/mcp-only.db"
    assert settings.host == "0.0.0.0"
    assert settings.port == 9900
    assert settings.mount_path == "/mcp"


def test_load_mcp_server_settings_rejects_invalid_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_mcp_env(monkeypatch)
    monkeypatch.setenv("MCP_TRANSPORT", "http")

    with pytest.raises(ValueError, match="Invalid MCP_TRANSPORT"):
        load_mcp_server_settings()


def test_load_mcp_server_settings_rejects_invalid_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_mcp_env(monkeypatch)
    monkeypatch.setenv("MCP_SERVER_PORT", "70000")

    with pytest.raises(ValueError, match="MCP_SERVER_PORT"):
        load_mcp_server_settings()
