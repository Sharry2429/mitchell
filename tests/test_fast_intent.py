import asyncio
from mitchell.core.fast_intent import resolve_intent

async def test_tier0_direct_match():
    # Direct alias match
    res = await resolve_intent("mute my laptop")
    assert isinstance(res, tuple)
    assert res[0] == "windows_hardware_set_volume"
    assert res[1] == {"level": 0}

async def test_tier1_llm_match():
    # Setup mock LLM that returns a tool call
    class MockProvider:
        async def call(self, messages, tools, max_tokens=None):
            from mitchell.providers.base import LLMResult
            from types import SimpleNamespace
            import json
            
            # Return a tool call to close notepad
            args = {"window_title": "notepad"}
            tc = SimpleNamespace(function=SimpleNamespace(name="windows_apps_close_window", arguments=json.dumps(args)))
            return LLMResult(content="", tool_calls=[tc])
            
    # Need to override active_provider
    import mitchell.core.fast_intent as fi
    old_active = fi.active_provider
    fi.active_provider = lambda: MockProvider()
    
    try:
        res = await resolve_intent("can you close the notepad app for me please")
        assert isinstance(res, tuple)
        assert res[0] == "windows_apps_close_window"
        assert res[1] == {"window_title": "notepad"}
    finally:
        fi.active_provider = old_active

if __name__ == "__main__":
    asyncio.run(test_tier0_direct_match())
    asyncio.run(test_tier1_llm_match())
    print("Fast intent tests passed!")
