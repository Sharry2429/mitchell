"""
Unified MCP Server exposing the same tool registry.
"""
import asyncio
import inspect
from mcp.server import Server
import mcp.server.stdio
from mcp.types import Tool, TextContent, CallToolResult
from mitchell.core.tool_registry import get_registry

# Initialize MCP Server
app = Server("Mitchell-MCP")

def _build_json_schema(func) -> dict:
    # A very basic schema generator for the port.
    # In a full implementation, this would inspect typing hints.
    return {
        "type": "object",
        "properties": {
            "args_json": {
                "type": "string",
                "description": "JSON arguments"
            }
        }
    }

@app.list_tools()
async def list_tools() -> list[Tool]:
    registry = get_registry()
    tools = []
    for name, func in registry.items():
        desc = inspect.getdoc(func) or f"Execute {name}"
        tools.append(Tool(
            name=name,
            description=desc,
            inputSchema=_build_json_schema(func)
        ))
    return tools

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    registry = get_registry()
    if name not in registry:
        raise ValueError(f"Unknown tool: {name}")
        
    func = registry[name]
    try:
        import json
        if "args_json" in arguments:
            args = json.loads(arguments["args_json"])
        else:
            args = arguments
            
        result = func(**args)
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main_async():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
