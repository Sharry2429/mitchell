"""Skill and Memory tools for Mitchell ToolRegistry."""

import json
from typing import Optional
from mitchell.memory.long_term import long_term_memory
from mitchell.memory.self_model import self_model
from mitchell.skills.executor import skill_executor
from mitchell.skills.library import skill_library
from mitchell.tools.registry import Tool


def skill_execute(skill_name: str, parameters_json: Optional[str] = None) -> str:
    """Execute a stored procedural skill by name with JSON parameters."""
    params = {}
    if parameters_json:
        try:
            params = json.loads(parameters_json)
        except Exception as e:
            return f"Invalid parameters JSON: {e}"

    res = skill_executor.execute(skill_name, parameters=params)
    if res.get("success"):
        return f"Skill '{skill_name}' completed successfully in {res.get('duration_s')}s"
    return f"Skill '{skill_name}' failed: {res.get('error')}"


def skill_list() -> str:
    """List all registered procedural skills in Mitchell's Skill Library."""
    skills = skill_library.list_skills()
    if not skills:
        return "Skill library is empty."
    lines = ["Available Skills:"]
    for s in skills:
        lines.append(f"  • {s.name} (v{s.version}, {len(s.steps)} steps): {s.description}")
    return "\n".join(lines)


def memory_remember(category: str, key: str, content: str) -> str:
    """Store a fact or user preference in Long-Term Memory."""
    entry = long_term_memory.remember(category=category, key=key, content=content)
    return f"Stored memory [{entry.category}] {entry.key} -> '{entry.content}'"


def memory_recall(category: str, key: str) -> str:
    """Recall a specific memory from Long-Term Memory."""
    val = long_term_memory.recall(category=category, key=key)
    if val:
        return f"[{category}:{key}] {val}"
    return f"No memory found for [{category}:{key}]"


def self_model_status() -> str:
    """Show capability stats and confidence from Mitchell's Self-Model."""
    caps = self_model.list_all()
    lines = ["Self-Model Capabilities & Confidence:"]
    for c in caps:
        lines.append(
            f"  • {c.capability_name} ({c.category}) | Confidence: {c.confidence:.2f} | Success Rate: {c.success_rate}% ({c.total_runs} runs)"
        )
    return "\n".join(lines)


# Tool definitions
exec_tool = Tool(
    name="skill_execute",
    description="Execute a multi-step procedural skill from Mitchell Skill Library.",
    parameters={
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "Name of the skill to execute"},
            "parameters_json": {"type": "string", "description": "Optional JSON string of input parameters"},
        },
        "required": ["skill_name"],
    },
    function=skill_execute,
)

list_tool = Tool(
    name="skill_list",
    description="List all available procedural skills.",
    parameters={"type": "object", "properties": {}},
    function=skill_list,
)

remember_tool = Tool(
    name="memory_remember",
    description="Store a fact, preference, or project context in Long-Term Memory.",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Category (preference, fact, project, config)"},
            "key": {"type": "string", "description": "Unique key"},
            "content": {"type": "string", "description": "Information to remember"},
        },
        "required": ["category", "key", "content"],
    },
    function=memory_remember,
)

recall_tool = Tool(
    name="memory_recall",
    description="Recall a stored fact or preference from Long-Term Memory.",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Category"},
            "key": {"type": "string", "description": "Unique key"},
        },
        "required": ["category", "key"],
    },
    function=memory_recall,
)

self_tool = Tool(
    name="self_model_status",
    description="Inspect Mitchell's internal Self-Model, capabilities, and success rates.",
    parameters={"type": "object", "properties": {}},
    function=self_model_status,
)

TOOLS = [exec_tool, list_tool, remember_tool, recall_tool, self_tool]
