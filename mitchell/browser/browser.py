"""
mitchell.browser.browser
========================
Browser control via Playwright — DOM/API-based, NO vision needed (the cheap,
fast path for anything scriptable). A single shared BrowserSession is reused
across calls; headless by default so it never grabs the user's screen.

These are module-level async functions so they register as clean MCP tools.
"""
from __future__ import annotations

from playwright.async_api import async_playwright

from mitchell.core.result import MCPResult

# module-level singleton so multiple tool calls share one browser/page
_session: dict | None = None


async def _get_session() -> dict:
    global _session
    if _session is None:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        _session = {"pw": pw, "browser": browser, "page": page, "url": None}
    return _session


async def browser_navigate(url: str) -> MCPResult:
    s = await _get_session()
    await s["page"].goto(url, wait_until="domcontentloaded", timeout=30000)
    s["url"] = url
    return MCPResult.success(data=f"Navigated to {url}")


async def browser_title() -> MCPResult:
    s = await _get_session()
    title = await s["page"].title()
    return MCPResult.success(data=f"Title: {title}")


async def browser_current_url() -> MCPResult:
    s = await _get_session()
    return MCPResult.success(data=s["page"].url)


async def browser_extract_text() -> MCPResult:
    """"Lightning-fast DOM text extraction — no vision needed."""
    s = await _get_session()
    text = await s["page"].inner_text("body")
    return MCPResult.success(data=text)


async def browser_get_text(selector: str) -> MCPResult:
    s = await _get_session()
    try:
        text = await s["page"].inner_text(selector)
        return MCPResult.success(data=text)
    except Exception as e:  # noqa: BLE001
        return MCPResult.fail(error=f"Selector '{selector}' not found: {e}")


async def browser_click(selector: str) -> MCPResult:
    s = await _get_session()
    try:
        await s["page"].click(selector, timeout=8000)
        return MCPResult.success(data=f"Clicked {selector}")
    except Exception as e:  # noqa: BLE001
        return MCPResult.fail(error=str(e))


async def browser_type(selector: str, text: str) -> MCPResult:
    s = await _get_session()
    try:
        await s["page"].fill(selector, text)
        return MCPResult.success(data=f"Typed into {selector}")
    except Exception as e:  # noqa: BLE001
        return MCPResult.fail(error=str(e))


async def browser_screenshot(path: str) -> MCPResult:
    s = await _get_session()
    await s["page"].screenshot(path=path)
    return MCPResult.success(data=f"Screenshot saved to {path}")


async def browser_stop() -> MCPResult:
    global _session
    if _session:
        await _session["browser"].close()
        await _session["pw"].stop()
        _session = None
    return MCPResult.success(data="Browser closed")


async def browser_search(query: str) -> MCPResult:
    """Quick end-to-end: send a search to the browser's default search UI."""
    s = await _get_session()
    await s["page"].goto("https://duckduckgo.com/", wait_until="domcontentloaded", timeout=30000)
    await s["page"].fill('input[name="q"]', query)
    await s["page"].keyboard.press("Enter")
    await s["page"].wait_for_load_state("domcontentloaded", timeout=20000)
    text = await s["page"].inner_text("body")
    return MCPResult.success(data=text[:1500])
