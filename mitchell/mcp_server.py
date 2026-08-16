"""
mitchell.mcp_server
Unified MCP Server entrypoint.
"""
from mitchell.core.tool_registry import mcp

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
