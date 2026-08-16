"""
Fast path (fast_do): lean single-thread loop, envelope sanitization, tool
chaining. Deterministic — no live LLM.
"""
import asyncio
import json
from types import SimpleNamespace

from mitchell.core.fast import fast_do, _looks_like_envelope
from mitchell.core.llm_client import LLMResult
from mitchell.core.tool_provider import StaticToolProvider


def _tc(name, args):
    return SimpleNamespace(id="c1", function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def _make_call(script):
    """script: list of responses, consumed in order; last returns final text."""
    calls = {"n": 0}

    async def fake_call(role, messages=None, tools=None, task_id=None):
        i = calls["n"]; calls["n"] += 1
        step = script[i] if i < len(script) else script[-1]
        if step["kind"] == "tool":
            return LLMResult(content="", tool_calls=[_tc(step["tool"], step.get("args", {}))])
        return LLMResult(content=step["text"], tool_calls=None)

    return fake_call, calls


def _run(coro):
    return asyncio.run(coro)


def test_fast_do_chains_and_returns_clean_answer():
    store = {"saw": []}
    def do_tool(tag):
        def _f(**kw):
            store["saw"].append(tag); return f"result-of-{tag}"
        return _f
    tools = StaticToolProvider({"t1": do_tool("t1"), "t2": do_tool("t2")})
    call, _ = _make_call([
        {"kind": "tool", "tool": "t1"},
        {"kind": "tool", "tool": "t2", "args": {"x": 1}},
        {"kind": "final", "text": "The answer is 42."},
    ])
    res = _run(fast_do("task", tools, llm_call=call))
    # It chained TWO tool calls with an injected fake LLM, then gave a clean answer.
    assert res["answer"] == "The answer is 42."
    assert "t1" in store["saw"] and "t2" in store["saw"]


def test_fast_do_sanitizes_raw_envelope_from_answer():
    tools = StaticToolProvider({"t": lambda: "x"})
    call, _ = _make_call([
        {"kind": "tool", "tool": "t"},
        {"kind": "final", "text": "[TextContent(type='text', text='{raw}')] structure noise"},
    ])
    res = _run(fast_do("task", tools, llm_call=call))
    # The envelope-leading answer is dropped so we don't present raw MCP text.
    assert not res["answer"].startswith("[TextContent(")


def test_looks_like_envelope():
    assert _looks_like_envelope("[TextContent(type='text'")
    assert _looks_like_envelope("content=[TextContent(")
    assert _looks_like_envelope('{"ok":')
    assert not _looks_like_envelope("The page title is Example Domain")
