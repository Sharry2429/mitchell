"""Blackboard and Agent Team tools for Mitchell ToolRegistry."""

import json
from mitchell.hive.blackboard import blackboard
from mitchell.hive.teams import team_coordinator
from mitchell.tools.registry import Tool


def blackboard_post(topic: str, content: str) -> str:
    """Post an update, artifact, or finding to a shared Blackboard topic."""
    entry = blackboard.post(topic=topic, content=content, author="user")
    return f"Posted to Blackboard topic '{topic}' [ID: {entry.id}]"


def blackboard_read(topic: str) -> str:
    """Read recent postings from a Blackboard topic."""
    entries = blackboard.read_topic(topic=topic, limit=5)
    if not entries:
        return f"No entries found on topic '{topic}'"
    lines = [f"=== Blackboard Topic: {topic} ==="]
    for e in entries:
        lines.append(f"  [{e.author}] {e.content}")
    return "\n".join(lines)


def team_list() -> str:
    """List all available specialized agent teams."""
    teams = team_coordinator.list_teams()
    lines = ["Available Agent Teams:"]
    for t in teams:
        lines.append(f"  • {t['team_name']}: {t['description']} (Agents: {', '.join(t['agents'])})")
    return "\n".join(lines)


def team_dispatch(team_name: str, task: str) -> str:
    """Dispatch a collective task to a specialized agent team."""
    res = team_coordinator.dispatch_team(team_name=team_name, task=task)
    if res.get("status") == "success":
        return f"Team '{team_name}' completed task. Results: {json.dumps(res.get('results', {}))}"
    return f"Team dispatch failed: {res.get('error')}"


# Tool definitions
post_tool = Tool(
    name="blackboard_post",
    description="Post a message, finding, or artifact to the shared Hive Blackboard.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic name (e.g. 'findings', 'status')"},
            "content": {"type": "string", "description": "Content or text to post"},
        },
        "required": ["topic", "content"],
    },
    function=blackboard_post,
)

read_tool = Tool(
    name="blackboard_read",
    description="Read recent entries from a Hive Blackboard topic.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic name to read"},
        },
        "required": ["topic"],
    },
    function=blackboard_read,
)

list_teams_tool = Tool(
    name="team_list",
    description="List all available specialized Hive Agent Teams.",
    parameters={"type": "object", "properties": {}},
    function=team_list,
)

dispatch_team_tool = Tool(
    name="team_dispatch",
    description="Dispatch a collaborative workflow to an agent team (e.g. 'research_team', 'cross_device_team').",
    parameters={
        "type": "object",
        "properties": {
            "team_name": {"type": "string", "description": "Name of the team"},
            "task": {"type": "string", "description": "Task instruction for the team"},
        },
        "required": ["team_name", "task"],
    },
    function=team_dispatch,
)

TOOLS = [post_tool, read_tool, list_teams_tool, dispatch_team_tool]
