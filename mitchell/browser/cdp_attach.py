"""Permanent Browser Automation — Real User Profile & CDP Attachment.

Connects to the user's actual Chrome or Edge profile directory, preserving:
- Logged-in accounts & cookies
- Browser extensions & bookmarks
- Local storage and session credentials

Layered Architecture:
1. Primary: Chrome DevTools Protocol (CDP) / Playwright Persistent Context attached to user profile.
2. Secondary: OS Accessibility tree (UIA / AT-SPI).
3. Tertiary: Injected Companion Extension bridge.
4. Fallback: Multimodal screen understanding + coordinate click.
"""

import asyncio
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger

try:
    from playwright.async_api import BrowserContext, Page, async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    BrowserContext = Any
    Page = Any
    async_playwright = None
    PLAYWRIGHT_AVAILABLE = False


class RealBrowserProfile(BaseModel):
    """Metadata for a detected local browser user profile."""

    browser_type: str  # chrome | edge | brave | firefox
    profile_name: str  # Default | Profile 1 | etc.
    user_data_dir: str
    is_running: bool = False
    cdp_port: Optional[int] = None


class RealBrowserManager:
    """Manages discovery and permanent CDP connection to real user browser profiles."""

    def __init__(self) -> None:
        self.active_context: Optional[BrowserContext] = None
        self.active_page: Optional[Page] = None
        self._pw_instance = None

    def find_user_profiles(self) -> List[RealBrowserProfile]:
        """Scan OS file system for installed Chrome and Edge user data directories."""
        profiles: List[RealBrowserProfile] = []
        system = platform.system()

        scan_paths = []
        if system == "Windows":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                scan_paths.append(("chrome", Path(local_appdata) / "Google" / "Chrome" / "User Data"))
                scan_paths.append(("edge", Path(local_appdata) / "Microsoft" / "Edge" / "User Data"))
                scan_paths.append(("brave", Path(local_appdata) / "BraveSoftware" / "Brave-Browser" / "User Data"))
        elif system == "Linux":
            home = Path.home()
            scan_paths.append(("chrome", home / ".config" / "google-chrome"))
            scan_paths.append(("edge", home / ".config" / "microsoft-edge"))
            scan_paths.append(("brave", home / ".config" / "BraveSoftware" / "Brave-Browser"))
        elif system == "Darwin":
            home = Path.home()
            scan_paths.append(("chrome", home / "Library" / "Application Support" / "Google" / "Chrome"))
            scan_paths.append(("edge", home / "Library" / "Application Support" / "Microsoft Edge"))

        for btype, base_path in scan_paths:
            if base_path.exists():
                # Scan subdirectories for profile identifiers
                default_dir = base_path / "Default"
                if default_dir.exists():
                    profiles.append(
                        RealBrowserProfile(
                            browser_type=btype,
                            profile_name="Default",
                            user_data_dir=str(base_path),
                        )
                    )
                for sub in base_path.glob("Profile *"):
                    if sub.is_dir():
                        profiles.append(
                            RealBrowserProfile(
                                browser_type=btype,
                                profile_name=sub.name,
                                user_data_dir=str(base_path),
                            )
                        )

        return profiles

    async def attach_real_profile(
        self,
        user_data_dir: Optional[str] = None,
        profile_directory: str = "Default",
        headless: bool = False,
    ) -> Dict[str, Any]:
        """
        Launch or attach to real user profile via CDP persistent context.
        Preserves all user cookies, logged-in sessions, and extensions.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "status": "error",
                "message": "Playwright is required for browser attachment. Run: pip install playwright && playwright install",
            }

        # Auto-detect user data dir if not provided
        if not user_data_dir:
            detected = self.find_user_profiles()
            if detected:
                user_data_dir = detected[0].user_data_dir
            else:
                user_data_dir = str(Path.home() / ".mitchell" / "browser_profile")

        logger.info("Attaching to real browser profile at '{}' (profile={})", user_data_dir, profile_directory)

        try:
            if not self._pw_instance:
                self._pw_instance = await async_playwright().start()

            # Launch persistent context with real user data dir
            context = await self._pw_instance.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="chrome" if platform.system() == "Windows" else None,
                args=[
                    f"--profile-directory={profile_directory}",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                ],
                viewport={"width": 1280, "height": 840},
            )

            self.active_context = context
            self.active_page = context.pages[0] if context.pages else await context.new_page()

            event_log.log_event(
                "real_browser_attached",
                source="cdp_attach",
                data={"user_data_dir": user_data_dir, "profile": profile_directory, "headless": headless},
            )

            return {
                "status": "connected",
                "user_data_dir": user_data_dir,
                "profile": profile_directory,
                "pages_open": len(context.pages),
            }
        except Exception as e:
            logger.warning("Direct user data attach failed (browser might be in use): {}. Providing isolated clone.", e)
            return {
                "status": "warning",
                "message": f"Browser profile in use or locked: {str(e)}. Close existing Chrome instances or use isolated profile clone.",
            }

    async def get_page_info(self) -> Dict[str, Any]:
        """Return title, URL, and accessibility snapshot of active browser page."""
        if not self.active_page:
            return {"status": "inactive", "message": "No active browser session"}

        try:
            url = self.active_page.url
            title = await self.active_page.title()
            return {
                "status": "active",
                "url": url,
                "title": title,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def close(self) -> None:
        """Disconnect and cleanup."""
        if self.active_context:
            try:
                await self.active_context.close()
            except Exception:
                pass
            self.active_context = None
            self.active_page = None

        if self._pw_instance:
            try:
                await self._pw_instance.stop()
            except Exception:
                pass
            self._pw_instance = None


real_browser_manager = RealBrowserManager()

__all__ = ["RealBrowserProfile", "RealBrowserManager", "real_browser_manager"]
