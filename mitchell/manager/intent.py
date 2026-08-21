"""Intent parsing and fast rule-based recognition module."""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Intent(BaseModel):
    """Parsed user intent representation."""

    raw_input: str = Field(..., description="Original user prompt or command")
    action_type: str = Field(
        default="unknown",
        description="Identified intent action type: help, exit, list_tools, call_tool, list_agents, hive_message, list_events, list_skills, run_skill, remember, recall, self_model, unknown",
    )
    tool_name: Optional[str] = Field(default=None, description="Target tool name if action_type is call_tool")
    agent_name: Optional[str] = Field(default=None, description="Target agent ID if action_type is hive_message")
    skill_name: Optional[str] = Field(default=None, description="Target skill name if action_type is run_skill")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    confidence: float = Field(default=1.0, description="Confidence score of intent recognition")
    target_agents: List[str] = Field(default_factory=list, description="Target agents to execute intent")


def parse_tool_args(args_str: str) -> Dict[str, Any]:
    """Parse tool arguments from JSON, key=value pairs, or raw string."""
    args_str = args_str.strip()
    if not args_str:
        return {}

    # 1. Try parsing as JSON
    if (args_str.startswith("{") and args_str.endswith("}")) or (args_str.startswith("[") and args_str.endswith("]")):
        try:
            parsed = json.loads(args_str)
            if isinstance(parsed, dict):
                return parsed
            return {"args": parsed}
        except json.JSONDecodeError:
            pass

    # 2. Try parsing key=value pairs
    kv_pattern = re.findall(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))', args_str)
    if kv_pattern:
        params: Dict[str, Any] = {}
        for key, v1, v2, v3 in kv_pattern:
            val = v1 or v2 or v3
            params[key] = val
        return params

    # 3. Fallback: treat entire string as raw / message / input argument
    return {"raw": args_str, "message": args_str, "input": args_str}


def parse_fast_intent(user_input: str) -> Optional[Intent]:
    """Rule-based fast intent parser without calling an LLM."""
    text = user_input.strip()
    if not text:
        return None

    lower = text.lower()

    # Exit / Quit
    if lower in ("exit", "quit", ":q", "bye"):
        return Intent(raw_input=text, action_type="exit")

    # Help
    if lower in ("help", "?", "--help", "-h"):
        return Intent(raw_input=text, action_type="help")

    # List Tools
    if lower in ("list tools", "tools", "show tools", "list_tools"):
        return Intent(raw_input=text, action_type="list_tools")

    # List Agents
    if lower in ("list agents", "agents", "show agents", "list_agents", "hive agents"):
        return Intent(raw_input=text, action_type="list_agents")

    # List Events
    if lower in ("list events", "events", "show events", "recent events"):
        return Intent(raw_input=text, action_type="list_events")

    # List Skills
    if lower in ("list skills", "skills", "show skills", "list_skills"):
        return Intent(raw_input=text, action_type="list_skills")

    # Self-Model / Status
    if lower in ("self model", "self_model", "capabilities", "my capabilities"):
        return Intent(raw_input=text, action_type="self_model")

    # Run Skill: "run skill <name> <params>", "skill <name> <params>"
    skill_prefixes = ["run skill ", "skill "]
    for prefix in skill_prefixes:
        if lower.startswith(prefix):
            remainder = text[len(prefix):].strip()
            parts = remainder.split(maxsplit=1)
            if parts:
                skill_name = parts[0]
                args_str = parts[1] if len(parts) > 1 else ""
                params = parse_tool_args(args_str)
                return Intent(
                    raw_input=text,
                    action_type="run_skill",
                    skill_name=skill_name,
                    parameters=params,
                )

    # Memory: "remember <category> <key> <content>"
    if lower.startswith("remember "):
        remainder = text[9:].strip()
        parts = remainder.split(maxsplit=2)
        if len(parts) >= 3:
            return Intent(
                raw_input=text,
                action_type="remember",
                parameters={"category": parts[0], "key": parts[1], "content": parts[2]},
            )
        elif len(parts) == 1 or len(parts) == 2:
            return Intent(
                raw_input=text,
                action_type="remember",
                parameters={"category": "user", "key": "general", "content": remainder},
            )

    # Memory Recall: "recall <category> <key>"
    if lower.startswith("recall "):
        remainder = text[7:].strip()
        parts = remainder.split(maxsplit=1)
        if len(parts) >= 2:
            return Intent(
                raw_input=text,
                action_type="recall",
                parameters={"category": parts[0], "key": parts[1]},
            )
        else:
            return Intent(
                raw_input=text,
                action_type="recall",
                parameters={"query": remainder},
            )

    # Hive agent message routing: "agent <name> <msg>", "ask agent <name> <msg>", "hive <name> <msg>"
    agent_prefixes = ["ask agent ", "send agent ", "agent ", "hive "]
    for prefix in agent_prefixes:
        if lower.startswith(prefix):
            remainder = text[len(prefix):].strip()
            parts = remainder.split(maxsplit=1)
            if parts:
                agent_name = parts[0]
                msg = parts[1] if len(parts) > 1 else ""
                return Intent(
                    raw_input=text,
                    action_type="hive_message",
                    agent_name=agent_name,
                    parameters={"message": msg},
                )

    # Tool execution prefixes
    tool_prefixes = ["call tool ", "run tool ", "tool ", "call "]
    for prefix in tool_prefixes:
        if lower.startswith(prefix):
            remainder = text[len(prefix):].strip()
            parts = remainder.split(maxsplit=1)
            if parts:
                tool_name = parts[0]
                args_str = parts[1] if len(parts) > 1 else ""
                params = parse_tool_args(args_str)
                return Intent(
                    raw_input=text,
                    action_type="call_tool",
                    tool_name=tool_name,
                    parameters=params,
                )

    return None


__all__ = ["Intent", "parse_fast_intent", "parse_tool_args"]
