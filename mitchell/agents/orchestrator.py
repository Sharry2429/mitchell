"""
Dynamic multi-agent orchestrator.
"""
import asyncio
import json
import logging
from typing import Any
from mitchell.providers import active_provider
from mitchell.core.tool_registry import get_registry

logger = logging.getLogger(__name__)

def _get_pillar_for_tool(tool_name: str) -> str:
    if tool_name.startswith("windows_"): return "windows"
    if tool_name.startswith("android_"): return "android"
    if tool_name.startswith("browser_"): return "browser"
    return "core"

def _build_tool_schema(name: str, func: Any) -> dict:
    """Build a basic OpenAI tool schema from a function using its docstring."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": getattr(func, "__doc__", "") or f"Execute {name}",
            "parameters": {
                "type": "object",
                "properties": {
                    "args_json": {
                        "type": "string",
                        "description": "JSON string of arguments for this function. Skip if none."
                    }
                }
            }
        }
    }

def _get_tools_for_pillar(pillar: str) -> list[dict]:
    registry = get_registry()
    tools = []
    for name, func in registry.items():
        if _get_pillar_for_tool(name) == pillar:
            tools.append(_build_tool_schema(name, func))
    return tools

def _execute_tool(name: str, args: dict) -> Any:
    registry = get_registry()
    if name not in registry:
        return f"Error: Tool {name} not found"
    
    func = registry[name]
    try:
        # In a real implementation we'd use pydantic/inspect to parse args properly
        # For simplicity in this lean port, we pass kwargs if provided
        return func(**args)
    except Exception as e:
        return f"Error executing {name}: {e}"

async def classify_task(task: str) -> dict:
    """Cheap classification pass to determine agent shape."""
    # Simple heuristic
    task_lower = task.lower()
    needs_windows = any(k in task_lower for k in ["windows", "laptop", "pc", "volume", "mute", "desktop", "file", "app"])
    needs_android = any(k in task_lower for k in ["android", "phone", "adb", "sms", "notification"])
    needs_browser = any(k in task_lower for k in ["browser", "chrome", "web", "url", "navigate"])
    
    pillars = []
    if needs_windows: pillars.append("windows")
    if needs_android: pillars.append("android")
    if needs_browser: pillars.append("browser")
    
    if not pillars:
        pillars = ["windows"] # Default
        
    has_multiple_pillars = len(pillars) > 1
    has_multiple_steps = " and " in task_lower or " then " in task_lower or " after " in task_lower
    
    if not has_multiple_pillars and not has_multiple_steps:
        shape = "single_direct"
    elif not has_multiple_pillars and has_multiple_steps:
        shape = "single_loop"
    elif has_multiple_pillars and not " then " in task_lower and not " after " in task_lower:
        shape = "parallel"
    else:
        shape = "specialist"
        
    return {"shape": shape, "pillars": pillars}

async def _agent_loop(task: str, tools_schema: list[dict], max_turns: int = 5) -> str:
    messages = [{"role": "user", "content": task}]
    provider = active_provider()
    
    for _ in range(max_turns):
        result = await provider.call(messages=messages, tools=tools_schema)
        messages.append({"role": "assistant", "content": result.content, "tool_calls": result.tool_calls})
        
        if not result.tool_calls:
            return result.content
            
        for tc in result.tool_calls:
            args = {}
            if tc.function.arguments:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    pass
            
            tool_res = _execute_tool(tc.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": str(tool_res)
            })
            
    return "Reached maximum turns without completion."

async def execute(task: str) -> str:
    """Main orchestrator entry point."""
    classification = await classify_task(task)
    shape = classification["shape"]
    pillars = classification["pillars"]
    
    if shape == "single_direct":
        # Fast path
        tools = _get_tools_for_pillar(pillars[0])
        provider = active_provider()
        res = await provider.call(messages=[{"role": "user", "content": task}], tools=tools)
        if res.tool_calls:
            tc = res.tool_calls[0]
            args = {}
            if tc.function.arguments:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    pass
            out = _execute_tool(tc.function.name, args)
            return f"Executed {tc.function.name}. Result: {out}"
        return res.content
        
    elif shape == "single_loop":
        tools = _get_tools_for_pillar(pillars[0])
        return await _agent_loop(task, tools)
        
    elif shape == "parallel":
        # Dispatch to multiple agents concurrently
        tasks = []
        for p in pillars:
            tools = _get_tools_for_pillar(p)
            tasks.append(_agent_loop(f"Extract and execute your part for: {task}", tools))
        results = await asyncio.gather(*tasks)
        return "\n".join(f"[{p}] {r}" for p, r in zip(pillars, results))
        
    elif shape == "specialist":
        # Simple dependent execution (sequential for now)
        results = []
        for p in pillars:
            tools = _get_tools_for_pillar(p)
            res = await _agent_loop(f"Task: {task}\nPrevious results: {results}\nExecute your part.", tools)
            results.append(res)
        return "\n".join(results)
        
    return "Unknown shape."
