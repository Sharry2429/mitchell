"""Entry point for running Mitchell MCP Server via `python -m mitchell.mcp`."""

import asyncio
from mitchell.mcp.server import MitchellMCPServer


def main() -> None:
    """Run Mitchell MCP server on stdio."""
    server = MitchellMCPServer()
    try:
        asyncio.run(server.run_stdio())
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == "__main__":
    main()
