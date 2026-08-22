"""Multi-channel notification dispatcher (Desktop toast, Telegram, Discord, Terminal)."""

import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class NotificationGateway:
    """Dispatches notifications across desktop toasts, Discord webhooks, Telegram, and audio alerts."""

    def __init__(self) -> None:
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    def send_desktop_toast(self, title: str, message: str) -> bool:
        """Send a native OS desktop notification."""
        try:
            if sys.platform == "win32":
                # Use powershell BurntToast or balloon if available, or print fallback
                ps_cmd = f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null'
                # Simple fallback
                print(f"🔔 [TOAST] {title}: {message}")
                return True
            elif sys.platform == "darwin":
                # macOS osascript
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=False)
                return True
            elif sys.platform.startswith("linux"):
                # Linux notify-send
                subprocess.run(["notify-send", title, message], check=False)
                return True
        except Exception as e:
            logger.debug("Desktop toast error: {}", e)

        print(f"🔔 {title}: {message}")
        return True

    def send_telegram(self, message: str) -> bool:
        """Send a message to a Telegram chat if token/chat_id are configured."""
        if not (self.telegram_bot_token and self.telegram_chat_id and HAS_REQUESTS):
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            logger.error("Telegram notify failed: {}", e)
            return False

    def send_discord(self, message: str) -> bool:
        """Send a message to a Discord channel via webhook URL."""
        if not (self.discord_webhook_url and HAS_REQUESTS):
            return False

        payload = {"content": message}
        try:
            res = requests.post(self.discord_webhook_url, json=payload, timeout=10)
            return res.status_code in (200, 204)
        except Exception as e:
            logger.error("Discord notify failed: {}", e)
            return False

    def notify_all(self, title: str, message: str) -> Dict[str, bool]:
        """Broadcast alert to all configured notification channels."""
        results = {
            "desktop": self.send_desktop_toast(title, message),
            "telegram": self.send_telegram(f"*{title}*\n{message}"),
            "discord": self.send_discord(f"**{title}**\n{message}"),
        }
        event_log.log_event(
            "notification_sent",
            source="notification_gateway",
            data={"title": title, "results": results},
        )
        return results


notifier = NotificationGateway()

__all__ = ["NotificationGateway", "notifier"]
