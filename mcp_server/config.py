from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

MCPTransport = Literal["stdio", "sse", "streamable-http"]

_ALLOWED_TRANSPORTS: set[str] = {"stdio", "sse", "streamable-http"}


@dataclass(frozen=True)
class MCPServerSettings:
    server_name: str
    transport: MCPTransport
    backend_base_url: str
    database_url: str | None
    host: str
    port: int
    mount_path: str


def _parse_transport(value: str) -> MCPTransport:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_TRANSPORTS:
        raise ValueError(
            "Invalid MCP_TRANSPORT. "
            f"Expected one of {sorted(_ALLOWED_TRANSPORTS)}, got '{value}'."
        )
    return normalized  # type: ignore[return-value]


def _parse_port(value: str) -> int:
    parsed = int(value)
    if parsed < 1 or parsed > 65535:
        raise ValueError("MCP_SERVER_PORT must be between 1 and 65535.")
    return parsed


def load_mcp_server_settings() -> MCPServerSettings:
    server_name = os.getenv("MCP_SERVER_NAME", "Research Copilot MCP")
    transport = _parse_transport(os.getenv("MCP_TRANSPORT", "stdio"))

    backend_base_url = os.getenv("MCP_BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    if not backend_base_url:
        raise ValueError("MCP_BACKEND_BASE_URL must not be empty.")

    # Reuse existing backend database configuration by default.
    database_url = os.getenv("MCP_DATABASE_URL") or os.getenv("DATABASE_URL")

    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = _parse_port(os.getenv("MCP_SERVER_PORT", "8811"))
    mount_path = os.getenv("MCP_MOUNT_PATH", "/")

    return MCPServerSettings(
        server_name=server_name,
        transport=transport,
        backend_base_url=backend_base_url,
        database_url=database_url,
        host=host,
        port=port,
        mount_path=mount_path,
    )
