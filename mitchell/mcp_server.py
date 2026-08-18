"""
mitchell.mcp_server
Unified MCP Server entrypoint.
"""
from mitchell.core.tool_registry import mcp
from mitchell.core.daemon import ensure_api_running

def main():
    # Ensure the Mitchell local API router is running in the background
    ensure_api_running()
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
