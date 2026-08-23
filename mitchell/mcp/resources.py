"""MCP Resources Provider for Mitchell AI.

Exposes live operational context, blackboard state, workspace files,
memory self-model, and device telemetry via MCP URIs.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.blackboard import blackboard
from mitchell.ide.project import project_scaffolder

from mitchell.mcp.protocol import MCPResource, MCPResourceContent
from mitchell.memory.self_model import self_model
from mitchell.workspace.documents import document_engine


class MCPResourceManager:
    """Manages MCP resources exposed by Mitchell AI."""

    def __init__(self) -> None:
        self.root_dir = Path(__file__).resolve().parent.parent.parent

    def list_resources(self) -> List[MCPResource]:
        """Return list of standard MCP resources."""
        return [
            MCPResource(
                uri="mitchell://system/status",
                name="Mitchell System Telemetry & Status",
                description="Live system uptime, active agents, cost, and event counters.",
            ),
            MCPResource(
                uri="mitchell://workspace/tree",
                name="Workspace Directory Tree",
                description="Recursive file and directory structure of active project.",
            ),
            MCPResource(
                uri="mitchell://blackboard/state",
                name="Hive Blackboard State",
                description="Shared blackboard variables, active tasks, and cross-agent findings.",
            ),
            MCPResource(
                uri="mitchell://memory/self_model",
                name="Mitchell Self-Model & Identity",
                description="Self-model capabilities, pillar definitions, and learned skills.",
            ),
            MCPResource(
                uri="mitchell://documents/list",
                name="Workspace Documents",
                description="Catalog of native co-authored markdown and research documents.",
            ),
        ]

    def read_resource(self, uri: str) -> Optional[MCPResourceContent]:
        """Read resource content by URI."""
        try:
            if uri == "mitchell://system/status":
                data = {
                    "system": "Mitchell Autonomous Multi-Agent Hive",
                    "status": "online",
                    "blackboard_topics": blackboard.list_topics(),
                    "events_logged": len(event_log.get_recent(50)),
                }
                return MCPResourceContent(uri=uri, text=json.dumps(data, indent=2))


            elif uri == "mitchell://workspace/tree":
                tree = project_scaffolder.get_directory_tree(self.root_dir, max_depth=3)
                return MCPResourceContent(uri=uri, text=json.dumps(tree, indent=2))

            elif uri == "mitchell://blackboard/state":
                state = blackboard.dump_state()
                return MCPResourceContent(uri=uri, text=json.dumps(state, indent=2))


            elif uri == "mitchell://memory/self_model":
                info = self_model.get_full_model() if hasattr(self_model, "get_full_model") else {"identity": "Mitchell"}
                return MCPResourceContent(uri=uri, text=json.dumps(info, indent=2))

            elif uri == "mitchell://documents/list":
                docs = document_engine.list_documents()
                data = [{"doc_id": d.doc_id, "title": d.title, "tags": d.tags, "updated_at": d.updated_at} for d in docs]
                return MCPResourceContent(uri=uri, text=json.dumps(data, indent=2))

            return None
        except Exception as e:
            logger.error("Failed to read MCP resource '{}': {}", uri, e)
            return MCPResourceContent(uri=uri, text=json.dumps({"error": str(e)}))


mcp_resource_manager = MCPResourceManager()

__all__ = ["MCPResourceManager", "mcp_resource_manager"]
