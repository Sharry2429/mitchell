"""Captcha detection heuristics and escalation handler."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger

CAPTCHA_SELECTORS = [
    # Cloudflare Turnstile / Challenge
    'iframe[src*="challenges.cloudflare.com"]',
    '#cf-challenge',
    '.cf-turnstile',
    'div[class*="cf-turnstile"]',
    '#challenge-running',
    '#challenge-stage',
    # Google reCAPTCHA
    'iframe[src*="google.com/recaptcha"]',
    'iframe[src*="recaptcha.net"]',
    '.g-recaptcha',
    '#g-recaptcha-response',
    # hCaptcha
    'iframe[src*="hcaptcha.com"]',
    '.h-captcha',
    '#hcaptcha-form',
    # Geetest
    '.geetest_radar_tip',
    '.geetest_holder',
    # AWS WAF
    '#aws-waf-captcha',
    'div[class*="aws-waf"]',
    # Arkose Labs / FunCaptcha
    'iframe[src*="arkoselabs.com"]',
    '#fc-iframe-wrap',
]

CAPTCHA_TEXT_SIGNATURES = [
    "verify you are human",
    "checking if the site connection is secure",
    "attention required! | cloudflare",
    "complete the security check",
    "please solve this puzzle",
    "security verification",
    "prove you are not a robot",
]


async def detect_captcha(page: Any) -> Optional[Dict[str, Any]]:
    """Scan page for common captcha widgets, iframes, or challenge messages."""
    try:
        # 1. Check known selectors
        for selector in CAPTCHA_SELECTORS:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=300):
                    return {
                        "detected": True,
                        "method": "selector",
                        "selector": selector,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception:
                continue

        # 2. Check visible text content in title or body
        title = (await page.title()).lower()
        for sig in CAPTCHA_TEXT_SIGNATURES:
            if sig in title:
                return {
                    "detected": True,
                    "method": "title_match",
                    "signature": sig,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        # Check body text snippet
        try:
            body_text = (await page.inner_text("body", timeout=500)).lower()[:1500]
            for sig in CAPTCHA_TEXT_SIGNATURES:
                if sig in body_text:
                    return {
                        "detected": True,
                        "method": "body_text",
                        "signature": sig,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
        except Exception:
            pass

    except Exception:
        pass

    return None


async def handle_captcha(
    page: Any,
    session_id: str = "default",
    on_escalate: Optional[Callable[[Dict[str, Any]], Any]] = None,
    timeout_seconds: int = 120,
) -> bool:
    """Escalate detected captcha: take screenshot, log event, and wait for resolution."""
    detection = await detect_captcha(page)
    if not detection:
        return True  # No captcha, proceed normally

    # Capture screenshot for visual inspection
    screenshot_dir = Path(settings.data_dir) / "captchas"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_file = screenshot_dir / f"captcha_{session_id}_{int(datetime.now().timestamp())}.png"

    try:
        await page.screenshot(path=str(screenshot_file), full_page=False)
        detection["screenshot"] = str(screenshot_file)
    except Exception:
        detection["screenshot"] = None

    logger.warning(
        "Captcha detected in session '{}' via {} (screenshot: {})",
        session_id,
        detection.get("method"),
        detection.get("screenshot"),
    )

    # Log to event log
    event_log.log_event(
        "captcha_detected",
        source=f"browser:{session_id}",
        data={**detection, "session_id": session_id},
    )

    # Notify callback (e.g. Manager / Orb bridge)
    if on_escalate:
        try:
            on_escalate(detection)
        except Exception:
            pass

    # Wait loop to check if captcha gets resolved
    logger.info("Paused browser session '{}'. Waiting for captcha resolution...", session_id)
    elapsed = 0
    poll_interval = 2
    while elapsed < timeout_seconds:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        current_check = await detect_captcha(page)
        if not current_check:
            logger.info("Captcha resolved successfully in session '{}'", session_id)
            event_log.log_event(
                "captcha_resolved",
                source=f"browser:{session_id}",
                data={"session_id": session_id, "duration_seconds": elapsed},
            )
            return True

    logger.error("Captcha resolution timed out after {}s in session '{}'", timeout_seconds, session_id)
    return False


__all__ = ["detect_captcha", "handle_captcha"]
