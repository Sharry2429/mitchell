from playwright.async_api import async_playwright
from mitchell.core.result import MCPResult

class BrowserSession:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

    async def stop(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def navigate(self, url: str) -> MCPResult:
        if not self.page:
            return MCPResult.fail("Browser not started")
        await self.page.goto(url)
        return MCPResult.success(f"Navigated to {url}")

    async def click(self, selector: str) -> MCPResult:
        if not self.page:
            return MCPResult.fail("Browser not started")
        await self.page.click(selector)
        return MCPResult.success(f"Clicked {selector}")

    async def type(self, selector: str, text: str) -> MCPResult:
        if not self.page:
            return MCPResult.fail("Browser not started")
        await self.page.fill(selector, text)
        return MCPResult.success(f"Typed into {selector}")

    async def screenshot(self, path: str) -> MCPResult:
        if not self.page:
            return MCPResult.fail("Browser not started")
        await self.page.screenshot(path=path)
        return MCPResult.success(f"Screenshot saved to {path}")
