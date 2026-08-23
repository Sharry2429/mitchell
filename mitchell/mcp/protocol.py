"""Model Context Protocol (MCP) JSON-RPC 2.0 Specifications & Type Definitions.

Implements official MCP Specification (2024-11-05).
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ── JSON-RPC 2.0 Base Models ───────────────────────────────────────────────

class JSONRPCRequest(BaseModel):
    """Standard JSON-RPC 2.0 Request."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class JSONRPCResponse(BaseModel):
    """Standard JSON-RPC 2.0 Response."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# ── MCP Tool Definitions ───────────────────────────────────────────────────

class MCPTool(BaseModel):
    """MCP Tool schema definition."""

    name: str
    description: str
    inputSchema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class MCPTextContent(BaseModel):
    """MCP Text Content payload."""

    type: str = "text"
    text: str


class MCPToolResult(BaseModel):
    """Result of an MCP tool execution."""

    content: List[MCPTextContent] = Field(default_factory=list)
    isError: bool = False


# ── MCP Resource Definitions ───────────────────────────────────────────────

class MCPResource(BaseModel):
    """MCP Resource metadata descriptor."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = "application/json"


class MCPResourceContent(BaseModel):
    """MCP Resource Content."""

    uri: str
    mimeType: Optional[str] = "application/json"
    text: str


# ── MCP Prompt Definitions ─────────────────────────────────────────────────

class MCPPromptArgument(BaseModel):
    """Argument specification for an MCP prompt."""

    name: str
    description: Optional[str] = None
    required: bool = False


class MCPPrompt(BaseModel):
    """MCP Prompt template definition."""

    name: str
    description: Optional[str] = None
    arguments: List[MCPPromptArgument] = Field(default_factory=list)


# Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

__all__ = [
    "JSONRPCRequest",
    "JSONRPCResponse",
    "MCPTool",
    "MCPTextContent",
    "MCPToolResult",
    "MCPResource",
    "MCPResourceContent",
    "MCPPrompt",
    "MCPPromptArgument",
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
]
