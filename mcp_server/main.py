from mcp_server.config import load_mcp_server_settings
from mcp_server.server import create_mcp_server


def main() -> int:
    settings = load_mcp_server_settings()
    server = create_mcp_server(settings)
    server.run(transport=settings.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
