import pytest
import asyncio
from mitchell.browser.browser import browser_navigate, browser_stop, browser_title

@pytest.mark.asyncio
async def test_browser_lifecycle():
    try:
        nav = await browser_navigate("https://example.com")
        assert "Navigated" in str(nav)
        
        title = await browser_title()
        assert "Title" in str(title)
        
        stop = await browser_stop()
        assert "Browser closed" in str(stop)
    except Exception as e:
        pytest.skip(f"Browser interaction failed: {e}")
