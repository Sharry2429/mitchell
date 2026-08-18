"""
mitchell.mcp_android
Android MCP Server entrypoint.
"""
from mitchell.core.tool_registry import create_mcp_server
from mitchell.core.daemon import ensure_api_running

def main():
    # Ensure the Mitchell local API router is running in the background
    ensure_api_running()
    mcp = create_mcp_server("android")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
