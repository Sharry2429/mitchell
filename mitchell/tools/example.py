"""Example echo tool demonstrating tool definition and auto-registration."""

from mitchell.tools.registry import Tool


def echo(message: str) -> str:
    """Return the input message."""
    return message


echo_tool = Tool(
    name="echo",
    description="Echoes the input message back.",
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to echo back",
            }
        },
        "required": ["message"],
    },
    function=echo,
)

# Exported TOOLS list for auto-discovery by ToolRegistry
TOOLS = [echo_tool]
