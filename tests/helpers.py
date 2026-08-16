"""Shared deterministic fakes for executor/verification tests.

Imported with plain ``from helpers import ...`` — pytest's default import mode
(prepend) puts the tests directory on sys.path, so no package init is needed.
"""
import json
from types import SimpleNamespace

from mitchell.core.llm_client import LLMResult


def tool_call(name: str, args: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def make_fake_llm(first_tool=None, final_text="Step output produced."):
    """Build a deterministic llm_call for the executor.

    Each executor step starts a fresh transcript. On the first call of a step we
    request ``first_tool`` (name, args) if given; once a tool result is present
    we finalize with ``final_text`` (no further tool calls). If ``first_tool``
    is None we never request tools and finalize immediately.
    """

    async def fake_llm(role, messages, tools=None, task_id=None):
        has_tool = any(m.get("role") == "tool" for m in messages)
        if has_tool:
            return LLMResult(content=final_text, tool_calls=None)
        if first_tool is not None:
            name, args = first_tool
            return LLMResult(content="", tool_calls=[tool_call(name, args)])
        return LLMResult(content=final_text, tool_calls=None)

    return fake_llm


def make_planner(steps, calls=None):
    """Build a deterministic planner that attaches ``steps`` to the task."""

    def _record():
        if calls is not None:
            calls.append(True)

    async def fake_planner(task):
        _record()
        task.steps = steps
        task.save()
        return task

    return fake_planner
