"""Browser automation tools for Mitchell ToolRegistry."""

import asyncio
from typing import Any, Dict, Optional
from mitchell.browser.engine import BrowserEngine
from mitchell.tools.registry import Tool

_engine = BrowserEngine(session_id="tools_default")


def _run_async(coro: Any) -> Any:
    """Run an async coroutine safely from sync tool context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except Exception:
        return asyncio.run(coro)


def browser_goto(url: str) -> str:
    """Navigate to a specified URL."""
    res = _run_async(_engine.goto(url))
    if res.get("success"):
        return f"Successfully navigated to {res.get('url')} (Title: {res.get('title')})"
    return f"Failed to navigate to {url}: {res.get('error')}"


def browser_click(selector: str) -> str:
    """Click an element matching the given CSS/XPath selector."""
    res = _run_async(_engine.click(selector, human=True))
    if res.get("success"):
        return f"Successfully clicked element '{selector}'"
    return f"Failed to click '{selector}': {res.get('error')}"


def browser_type(selector: str, text: str) -> str:
    """Type text into an input element."""
    res = _run_async(_engine.type_text(selector, text, human=True))
    if res.get("success"):
        return f"Successfully typed text into '{selector}'"
    return f"Failed to type into '{selector}': {res.get('error')}"


def browser_snapshot() -> str:
    """Take a structured text snapshot of the current page."""
    res = _run_async(_engine.snapshot())
    if res.get("success"):
        return res.get("content", "Empty snapshot")
    return f"Failed to take snapshot: {res.get('error')}"


def browser_screenshot(filename: Optional[str] = None) -> str:
    """Capture a screenshot of the current page."""
    res = _run_async(_engine.screenshot(filename=filename))
    if res.get("success"):
        return f"Screenshot saved to: {res.get('path')}"
    return f"Failed to take screenshot: {res.get('error')}"


# Tool definitions
goto_tool = Tool(
    name="browser_goto",
    description="Navigate to a webpage URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to navigate to"}
        },
        "required": ["url"],
    },
    function=browser_goto,
)

click_tool = Tool(
    name="browser_click",
    description="Click an element on the webpage using human-like mouse.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the element to click"}
        },
        "required": ["selector"],
    },
    function=browser_click,
)

type_tool = Tool(
    name="browser_type",
    description="Type text into an input field on the webpage.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of input field"},
            "text": {"type": "string", "description": "Text to type"},
        },
        "required": ["selector", "text"],
    },
    function=browser_type,
)

snapshot_tool = Tool(
    name="browser_snapshot",
    description="Get a clean text snapshot of interactive elements on the current page.",
    parameters={"type": "object", "properties": {}},
    function=browser_snapshot,
)

screenshot_tool = Tool(
    name="browser_screenshot",
    description="Take a screenshot of the current webpage.",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Optional custom filename"}
        },
    },
    function=browser_screenshot,
)

TOOLS = [goto_tool, click_tool, type_tool, snapshot_tool, screenshot_tool]
