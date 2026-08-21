"""Mitchell Browser Pillar package."""

from mitchell.browser.captcha import detect_captcha, handle_captcha
from mitchell.browser.engine import BrowserEngine
from mitchell.browser.mouse import HumanMouse, generate_bezier_curve, human_mouse
from mitchell.browser.session import (
    PLAYWRIGHT_AVAILABLE,
    BrowserSession,
    BrowserSessionManager,
    session_manager,
)
from mitchell.browser.stealth import apply_stealth

__all__ = [
    "BrowserEngine",
    "BrowserSession",
    "BrowserSessionManager",
    "session_manager",
    "HumanMouse",
    "human_mouse",
    "generate_bezier_curve",
    "apply_stealth",
    "detect_captcha",
    "handle_captcha",
    "PLAYWRIGHT_AVAILABLE",
]
