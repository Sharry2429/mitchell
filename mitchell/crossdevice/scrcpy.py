"""Wireless screen mirroring and big-screen app casting using scrcpy and ADB."""

import shutil
import subprocess
from typing import Any, Dict, Optional

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ScreenMirrorEngine:
    """Controls wireless mirroring, window positioning, and app projection via scrcpy."""

    def __init__(self) -> None:
        self.scrcpy_bin = settings.scrcpy_path or "scrcpy"

    def is_available(self) -> bool:
        """Check if scrcpy executable exists in PATH."""
        return bool(shutil.which(self.scrcpy_bin))

    def start_mirroring(
        self,
        stay_awake: bool = True,
        fullscreen: bool = False,
        window_title: str = "Mitchell Phone Screen",
    ) -> Dict[str, Any]:
        """Launch wireless screen mirroring window."""
        if not self.is_available():
            return {
                "status": "error",
                "message": f"scrcpy binary '{self.scrcpy_bin}' not found in system PATH. Install scrcpy for full screen casting.",
            }

        args = [self.scrcpy_bin, "--window-title", window_title]
        if stay_awake:
            args.append("--stay-awake")
        if fullscreen:
            args.append("--fullscreen")

        try:
            process = subprocess.Popen(args)
            event_log.log_event(
                "screen_mirroring_started",
                source="screen_mirror_engine",
                data={"title": window_title, "fullscreen": fullscreen},
            )
            logger.info("Launched scrcpy screen mirroring: {}", window_title)
            return {"status": "success", "pid": process.pid}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_app_on_big_screen(self, app_package_or_name: str) -> Dict[str, Any]:
        """Launch an app on the phone and mirror its window to the PC display."""
        from mitchell.android.engine import android_engine

        # 1. Launch on device via ADB
        if android_engine.is_connected():
            android_engine.launch_app(app_package_or_name)

        # 2. Mirror screen
        res = self.start_mirroring(window_title=f"Mitchell: {app_package_or_name}")
        return {
            "status": "success",
            "app": app_package_or_name,
            "mirror": res,
        }


screen_mirror_engine = ScreenMirrorEngine()

__all__ = ["ScreenMirrorEngine", "screen_mirror_engine"]
