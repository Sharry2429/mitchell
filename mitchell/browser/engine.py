"""High-level browser automation engine integrating stealth, human mouse, and captcha handling."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.browser.captcha import handle_captcha
from mitchell.browser.mouse import human_mouse
from mitchell.browser.session import BrowserSession, session_manager


class BrowserEngine:
    """High-level browser engine for automated task execution."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id

    async def _get_session(self, headless: Optional[bool] = None) -> BrowserSession:
        return await session_manager.get_or_create_session(
            session_id=self.session_id,
            headless=headless,
        )

    async def goto(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30000,
        headless: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Navigate to URL, handle anti-bot checks, and return page details."""
        session = await self._get_session(headless=headless)
        async with session.lock:
            page = session.page
            logger.info("Browser [{}]: Navigating to '{}'", self.session_id, url)

            try:
                response = await page.goto(url, wait_until=wait_until, timeout=timeout)
                status_code = response.status if response else 200

                # Captcha verification check
                await handle_captcha(page, session_id=self.session_id)

                title = await page.title()
                current_url = page.url

                event_log.log_event(
                    "browser_navigated",
                    source=f"browser:{self.session_id}",
                    data={"url": current_url, "title": title, "status": status_code},
                )

                return {
                    "success": True,
                    "url": current_url,
                    "title": title,
                    "status_code": status_code,
                }
            except Exception as e:
                logger.error("Browser [{}]: Navigation failed for '{}': {}", self.session_id, url, e)
                return {"success": False, "error": str(e), "url": url}

    async def click(
        self,
        selector: str,
        human: bool = True,
        timeout: int = 10000,
    ) -> Dict[str, Any]:
        """Click an element using human mouse or direct Playwright click."""
        session = await self._get_session()
        async with session.lock:
            page = session.page
            logger.info("Browser [{}]: Clicking selector '{}' (human={})", self.session_id, selector, human)
            try:
                if human:
                    success = await human_mouse.click_element(page, selector, timeout=timeout)
                else:
                    await page.click(selector, timeout=timeout)
                    success = True

                if success:
                    # Captcha check after click
                    await handle_captcha(page, session_id=self.session_id)

                return {"success": success, "selector": selector}
            except Exception as e:
                logger.error("Browser [{}]: Click failed on '{}': {}", self.session_id, selector, e)
                return {"success": False, "error": str(e), "selector": selector}

    async def type_text(
        self,
        selector: str,
        text: str,
        human: bool = True,
        clear_first: bool = True,
    ) -> Dict[str, Any]:
        """Type text into an input element."""
        session = await self._get_session()
        async with session.lock:
            page = session.page
            logger.info("Browser [{}]: Typing text into '{}' (length={})", self.session_id, selector, len(text))
            try:
                if human:
                    success = await human_mouse.type_text(page, selector, text, clear_first=clear_first)
                else:
                    if clear_first:
                        await page.fill(selector, text)
                    else:
                        await page.type(selector, text)
                    success = True
                return {"success": success, "selector": selector}
            except Exception as e:
                logger.error("Browser [{}]: Typing failed on '{}': {}", self.session_id, selector, e)
                return {"success": False, "error": str(e), "selector": selector}

    async def press_key(self, key: str) -> Dict[str, Any]:
        """Press a keyboard key."""
        session = await self._get_session()
        async with session.lock:
            page = session.page
            try:
                await page.keyboard.press(key)
                return {"success": True, "key": key}
            except Exception as e:
                return {"success": False, "error": str(e), "key": key}

    async def screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of the current page."""
        session = await self._get_session()
        async with session.lock:
            page = session.page
            screenshots_dir = Path(settings.data_dir) / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            fname = filename or f"screenshot_{self.session_id}_{int(datetime.now().timestamp())}.png"
            file_path = screenshots_dir / fname

            try:
                await page.screenshot(path=str(file_path), full_page=False)
                return {"success": True, "path": str(file_path)}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def snapshot(self, max_length: int = 4000) -> Dict[str, Any]:
        """Generate a clean text/DOM representation of visible interactive page elements."""
        session = await self._get_session()
        async with session.lock:
            page = session.page
            try:
                title = await page.title()
                url = page.url

                # Extract headings, links, inputs, and buttons
                elements = await page.evaluate("""
                    () => {
                        const items = [];
                        const nodes = document.querySelectorAll('h1, h2, h3, p, a, button, input, textarea, select');
                        for (const node of nodes) {
                            const rect = node.getBoundingClientRect();
                            if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(node).display === 'none') {
                                continue;
                            }
                            const tag = node.tagName.toLowerCase();
                            const text = (node.innerText || node.value || node.placeholder || '').trim();
                            if (!text && tag !== 'input') continue;
                            items.push({
                                tag: tag,
                                text: text.substring(0, 150),
                                id: node.id || undefined,
                                name: node.name || undefined,
                                href: node.href || undefined
                            });
                        }
                        return items.slice(0, 50);
                    }
                """)

                formatted_lines = [f"# Page Snapshot: {title}", f"URL: {url}", ""]
                for item in elements:
                    tag = item.get("tag", "").upper()
                    text = item.get("text", "")
                    ident = f"#{item['id']}" if item.get("id") else ""
                    formatted_lines.append(f"- [{tag}{ident}] {text}")

                content = "\n".join(formatted_lines)[:max_length]
                return {
                    "success": True,
                    "title": title,
                    "url": url,
                    "content": content,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def close(self) -> bool:
        """Close browser session."""
        return await session_manager.close_session(self.session_id)


browser_engine = BrowserEngine()

__all__ = ["BrowserEngine", "browser_engine"]
