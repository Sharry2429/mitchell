"""
Unified MCP Server exposing the same tool registry.
"""
from mitchell.core.tool_registry import mcp, discover_all_tools

def main():
    discover_all_tools()
    mcp.run()

if __name__ == "__main__":
    main()
