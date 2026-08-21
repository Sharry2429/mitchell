"""Multi-session manager for Playwright with persistent profiles, isolation, and locking."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.browser.stealth import apply_stealth

try:
    from playwright.async_api import BrowserContext, Page, async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    BrowserContext = Any
    Page = Any
    async_playwright = None
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class BrowserSession:
    """Individual isolated browser session with persistent context and locking."""

    session_id: str
    user_data_dir: Path
    headless: bool
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_open: bool = False

    def touch(self) -> None:
        """Update last active timestamp."""
        self.last_active = datetime.now(timezone.utc)


class BrowserSessionManager:
    """Manages multiple isolated browser profiles and lifecycles."""

    def __init__(self, base_profile_dir: Optional[Path] = None) -> None:
        self.base_profile_dir = Path(base_profile_dir or settings.browser_user_data_dir)
        self.base_profile_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, BrowserSession] = {}
        self._playwright_instance = None
        self._global_lock = asyncio.Lock()

    async def _ensure_playwright(self) -> Any:
        """Initialize playwright backend if not already active."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Install via: pip install playwright && playwright install")

        if self._playwright_instance is None:
            self._playwright_instance = await async_playwright().start()
        return self._playwright_instance

    async def get_or_create_session(
        self,
        session_id: str = "default",
        headless: Optional[bool] = None,
        viewport: Optional[Dict[str, int]] = None,
    ) -> BrowserSession:
        """Retrieve existing session or launch a new persistent isolated browser profile."""
        async with self._global_lock:
            if session_id in self._sessions and self._sessions[session_id].is_open:
                session = self._sessions[session_id]
                session.touch()
                return session

            pw = await self._ensure_playwright()
            profile_path = self.base_profile_dir / session_id
            profile_path.mkdir(parents=True, exist_ok=True)

            is_headless = settings.browser_headless if headless is None else headless
            vp = viewport or {"width": 1280, "height": 800}

            logger.info(
                "Launching browser session '{}' (headless={}, profile={})",
                session_id,
                is_headless,
                profile_path,
            )

            # Launch persistent context
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=is_headless,
                viewport=vp,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                ],
            )

            await apply_stealth(context)

            # Open or get initial page
            page = context.pages[0] if context.pages else await context.new_page()
            await apply_stealth(page)

            session = BrowserSession(
                session_id=session_id,
                user_data_dir=profile_path,
                headless=is_headless,
                context=context,
                page=page,
                is_open=True,
            )
            self._sessions[session_id] = session

            event_log.log_event(
                "browser_session_started",
                source="browser_manager",
                data={"session_id": session_id, "headless": is_headless, "profile": str(profile_path)},
            )

            return session

    async def close_session(self, session_id: str) -> bool:
        """Close an individual session and persist state to disk."""
        async with self._global_lock:
            session = self._sessions.get(session_id)
            if not session or not session.is_open:
                return False

            async with session.lock:
                try:
                    if session.context:
                        await session.context.close()
                except Exception as e:
                    logger.warning("Error closing context for session '{}': {}", session_id, e)
                finally:
                    session.is_open = False
                    session.context = None
                    session.page = None

            event_log.log_event(
                "browser_session_closed",
                source="browser_manager",
                data={"session_id": session_id},
            )
            logger.info("Closed browser session '{}'", session_id)
            return True

    async def close_all(self) -> None:
        """Close all active sessions and stop Playwright."""
        for session_id in list(self._sessions.keys()):
            await self.close_session(session_id)

        if self._playwright_instance:
            try:
                await self._playwright_instance.stop()
            except Exception:
                pass
            self._playwright_instance = None

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List active and known browser sessions."""
        return [
            {
                "session_id": s.session_id,
                "is_open": s.is_open,
                "headless": s.headless,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
                "profile_path": str(s.user_data_dir),
            }
            for s in self._sessions.values()
        ]


session_manager = BrowserSessionManager()

__all__ = ["BrowserSession", "BrowserSessionManager", "session_manager", "PLAYWRIGHT_AVAILABLE"]
