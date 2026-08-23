"""Comprehensive test suite for Mitchell Model Context Protocol (MCP) Server & Client package."""

import asyncio
import pytest

from mitchell.manager import Manager
from mitchell.mcp import (
    MitchellMCPClient,
    MitchellMCPServer,
    mcp_client,
    mcp_prompt_manager,
    mcp_resource_manager,
    mcp_server,
    mcp_tool_adapter,
)


def test_mcp_server_initialize():
    """Verify MCP initialize handshake and capabilities negotiation."""
    async def _test():
        server = MitchellMCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
        res = await server.handle_request(req)
        assert res is not None
        assert res["id"] == 1
        assert res["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in res["result"]["capabilities"]
        assert "resources" in res["result"]["capabilities"]
        assert "prompts" in res["result"]["capabilities"]

    asyncio.run(_test())


def test_mcp_server_tools_list():
    """Verify MCP tools/list exposes all tools across all Mitchell pillars."""
    async def _test():
        server = MitchellMCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        res = await server.handle_request(req)
        assert res is not None
        tools = res["result"]["tools"]
        assert len(tools) >= 15

        tool_names = [t["name"] for t in tools]
        # Check presence of multi-pillar tools
        assert "ide_terminal_run" in tool_names or "system_run_command" in tool_names
        assert "deep_research_execute" in tool_names
        assert "browser_real_profile_attach" in tool_names
        assert "windows_uia_click" in tool_names
        assert "agent_harness_dispatch" in tool_names
        assert "iot_call_service" in tool_names
        assert "document_generate_report" in tool_names
        assert "takeover_start_task" in tool_names

    asyncio.run(_test())


def test_mcp_server_tools_call():
    """Verify MCP tools/call dispatches and executes tools correctly."""
    async def _test():
        server = MitchellMCPServer()

        # Call document generation tool
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "document_generate_report",
                "arguments": {"topic": "MCP Integration Report"},
            },
        }
        res = await server.handle_request(req)
        assert res is not None
        assert "result" in res
        assert res["result"]["isError"] is False
        assert "Generated Document" in res["result"]["content"][0]["text"]

    asyncio.run(_test())


def test_mcp_server_resources_list_and_read():
    """Verify MCP resources/list and resources/read."""
    async def _test():
        server = MitchellMCPServer()

        # List resources
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {},
        }
        res = await server.handle_request(req)
        resources = res["result"]["resources"]
        assert len(resources) >= 4
        uris = [r["uri"] for r in resources]
        assert "mitchell://system/status" in uris
        assert "mitchell://workspace/tree" in uris

        # Read resource
        read_req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": "mitchell://system/status"},
        }
        read_res = await server.handle_request(read_req)
        assert read_res is not None
        assert "result" in read_res
        assert "contents" in read_res["result"]
        assert len(read_res["result"]["contents"]) > 0

    asyncio.run(_test())


def test_mcp_server_prompts_list_and_get():
    """Verify MCP prompts/list and prompts/get."""
    async def _test():
        server = MitchellMCPServer()

        # List prompts
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/list",
            "params": {},
        }
        res = await server.handle_request(req)
        prompts = res["result"]["prompts"]
        assert len(prompts) >= 2
        names = [p["name"] for p in prompts]
        assert "karpathy_principles" in names
        assert "autonomous_takeover" in names

        # Get prompt
        get_req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "prompts/get",
            "params": {"name": "karpathy_principles"},
        }
        get_res = await server.handle_request(get_req)
        assert get_res is not None
        assert "result" in get_res
        assert len(get_res["result"]["messages"]) > 0

    asyncio.run(_test())


def test_mcp_client_operations():
    """Verify MitchellMCPClient wrapper methods."""
    async def _test():
        client = MitchellMCPClient()
        tools = await client.list_tools()
        assert len(tools) >= 15

        res = await client.call_tool("document_generate_report", {"topic": "Client Test Document"})
        assert res["isError"] is False

        resources = await client.list_resources()
        assert len(resources) >= 4

        status_text = await client.read_resource("mitchell://system/status")
        assert status_text is not None
        assert "Mitchell" in status_text

    asyncio.run(_test())


def test_manager_loop_mcp_tool_execution():
    """Verify Manager loop executes commands via MCP Tool Adapter."""
    mgr = Manager()
    response = mgr.receive("run tool document_generate_report topic='Quarterly Architecture Audit'")
    assert "Result: Generated Document" in response
