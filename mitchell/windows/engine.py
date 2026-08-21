"""Windows controller engine using pywinauto UIA/Win32 and desktop mouse."""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.windows.mouse import desktop_mouse

try:
    import pywinauto
    from pywinauto import Desktop, Application
    from pywinauto.findwindows import find_windows
    from pywinauto.keyboard import send_keys as pywinauto_send_keys
    PYWINAUTO_AVAILABLE = True
except ImportError:
    pywinauto = None
    Desktop = None
    Application = None
    find_windows = None
    pywinauto_send_keys = None
    PYWINAUTO_AVAILABLE = False


class WindowsEngine:
    """Controls Windows desktop applications, windows, and UI automation elements."""

    def __init__(self, backend: str = "uia") -> None:
        self.backend = backend

    def launch_app(self, cmd_or_path: str, timeout: int = 15) -> Dict[str, Any]:
        """Launch an application process."""
        logger.info("Windows: Launching application '{}'", cmd_or_path)
        try:
            if PYWINAUTO_AVAILABLE:
                app = Application(backend=self.backend).start(cmd_or_path, timeout=timeout)
                pid = app.process
            else:
                proc = subprocess.Popen(cmd_or_path, shell=True)
                pid = proc.pid

            event_log.log_event(
                "windows_app_launched",
                source="windows_engine",
                data={"cmd": cmd_or_path, "pid": pid},
            )
            return {"success": True, "pid": pid, "cmd": cmd_or_path}
        except Exception as e:
            logger.error("Windows: Failed to launch '{}': {}", cmd_or_path, e)
            return {"success": False, "error": str(e), "cmd": cmd_or_path}

    def list_windows(self) -> List[Dict[str, Any]]:
        """List all visible top-level desktop windows."""
        if not PYWINAUTO_AVAILABLE:
            return []

        windows_info: List[Dict[str, Any]] = []
        try:
            desktop = Desktop(backend=self.backend)
            for win in desktop.windows():
                if win.is_visible():
                    try:
                        title = win.window_text().strip()
                        if title:
                            rect = win.rectangle()
                            windows_info.append({
                                "handle": win.handle,
                                "title": title,
                                "class_name": win.class_name(),
                                "process_id": win.process_id(),
                                "rect": {
                                    "left": rect.left,
                                    "top": rect.top,
                                    "width": rect.width(),
                                    "height": rect.height(),
                                },
                            })
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("Windows: Error listing windows: {}", e)

        return windows_info

    def find_window(self, title_query: str) -> Optional[Any]:
        """Find top-level window by title substring."""
        if not PYWINAUTO_AVAILABLE:
            return None

        desktop = Desktop(backend=self.backend)
        lower_query = title_query.lower()
        for win in desktop.windows():
            try:
                if win.is_visible() and lower_query in win.window_text().lower():
                    return win
            except Exception:
                continue
        return None

    def focus_window(self, title_query: str) -> Dict[str, Any]:
        """Bring window to foreground and set active focus."""
        win = self.find_window(title_query)
        if not win:
            return {"success": False, "error": f"Window matching '{title_query}' not found"}

        try:
            win.set_focus()
            title = win.window_text()
            logger.info("Windows: Focused window '{}'", title)
            event_log.log_event(
                "windows_focused",
                source="windows_engine",
                data={"title": title, "handle": win.handle},
            )
            return {"success": True, "title": title, "handle": win.handle}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def inspect_tree(self, title_query: Optional[str] = None, max_items: int = 40) -> Dict[str, Any]:
        """Extract accessibility control hierarchy for a window or active desktop."""
        if not PYWINAUTO_AVAILABLE:
            return {"success": False, "error": "pywinauto not available"}

        win = self.find_window(title_query) if title_query else None
        target = win if win else Desktop(backend=self.backend)

        elements: List[Dict[str, Any]] = []
        try:
            descendants = target.descendants() if hasattr(target, "descendants") else []
            for elem in descendants[:max_items]:
                try:
                    if elem.is_visible():
                        name = elem.window_text().strip()
                        ctrl_type = elem.element_info.control_type if hasattr(elem.element_info, "control_type") else elem.class_name()
                        auto_id = getattr(elem.element_info, "automation_id", "")
                        rect = elem.rectangle()

                        if name or auto_id or ctrl_type in ("Button", "Edit", "MenuItem", "ComboBox"):
                            elements.append({
                                "name": name[:80],
                                "control_type": ctrl_type,
                                "automation_id": auto_id,
                                "rect": {
                                    "left": rect.left,
                                    "top": rect.top,
                                    "width": rect.width(),
                                    "height": rect.height(),
                                },
                            })
                except Exception:
                    continue

            return {
                "success": True,
                "window": win.window_text() if win else "Desktop",
                "count": len(elements),
                "elements": elements,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click_element(
        self,
        title_query: Optional[str] = None,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        control_type: Optional[str] = None,
        human: bool = True,
    ) -> Dict[str, Any]:
        """Click UI element matching criteria using human desktop mouse."""
        if not PYWINAUTO_AVAILABLE:
            return {"success": False, "error": "pywinauto not available"}

        win = self.find_window(title_query) if title_query else None
        root = win if win else Desktop(backend=self.backend)

        try:
            if win:
                win.set_focus()

            for elem in root.descendants():
                try:
                    if not elem.is_visible():
                        continue

                    e_name = elem.window_text().strip().lower()
                    e_auto_id = getattr(elem.element_info, "automation_id", "").lower()
                    e_type = getattr(elem.element_info, "control_type", "").lower()

                    match_name = name.lower() in e_name if name else True
                    match_id = automation_id.lower() in e_auto_id if automation_id else True
                    match_type = control_type.lower() == e_type if control_type else True

                    if (name or automation_id or control_type) and match_name and match_id and match_type:
                        rect = elem.rectangle()
                        rect_dict = {
                            "left": rect.left,
                            "top": rect.top,
                            "width": rect.width(),
                            "height": rect.height(),
                        }

                        if human:
                            desktop_mouse.click_rect(rect_dict)
                        else:
                            elem.click_input()

                        logger.info("Windows: Clicked element '{}' ({})", elem.window_text(), e_type)
                        event_log.log_event(
                            "windows_element_clicked",
                            source="windows_engine",
                            data={"name": elem.window_text(), "control_type": e_type, "rect": rect_dict},
                        )
                        return {"success": True, "element": elem.window_text(), "control_type": e_type}
                except Exception:
                    continue

            return {"success": False, "error": f"Element matching (name={name}, id={automation_id}, type={control_type}) not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(
        self,
        text: str,
        title_query: Optional[str] = None,
        name: Optional[str] = None,
        human: bool = True,
    ) -> Dict[str, Any]:
        """Type text into targeted window or focused control."""
        if title_query:
            win = self.find_window(title_query)
            if win:
                win.set_focus()

        if name:
            self.click_element(title_query=title_query, name=name, human=human)

        try:
            logger.info("Windows: Typing text (length={})", len(text))
            if human:
                for char in text:
                    if PYWINAUTO_AVAILABLE and pywinauto_send_keys:
                        # Escape special pywinauto characters
                        clean_char = char if char not in "{}+^%~()" else f"{{{char}}}"
                        pywinauto_send_keys(clean_char, with_spaces=True, pause=0.0)
                    time.sleep(0.04 + (0.08 if char in " .," else 0.02))
            else:
                if PYWINAUTO_AVAILABLE and pywinauto_send_keys:
                    pywinauto_send_keys(text, with_spaces=True)

            event_log.log_event(
                "windows_typed_text",
                source="windows_engine",
                data={"length": len(text), "target": title_query or "active"},
            )
            return {"success": True, "text_length": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_keys(self, keys_str: str) -> Dict[str, Any]:
        """Send special key sequence (e.g. '{ENTER}', '^s', '%{F4}')."""
        if not PYWINAUTO_AVAILABLE or not pywinauto_send_keys:
            return {"success": False, "error": "pywinauto not available"}
        try:
            pywinauto_send_keys(keys_str, with_spaces=True)
            return {"success": True, "keys": keys_str}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def screenshot_window(self, title_query: Optional[str] = None, filename: Optional[str] = None) -> Dict[str, Any]:
        """Capture screenshot of a specific window or full desktop."""
        screenshots_dir = Path(settings.data_dir) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"win_screenshot_{int(datetime.now().timestamp())}.png"
        filepath = screenshots_dir / fname

        try:
            from PIL import ImageGrab
            win = self.find_window(title_query) if title_query else None
            if win:
                rect = win.rectangle()
                bbox = (rect.left, rect.top, rect.right, rect.bottom)
                img = ImageGrab.grab(bbox=bbox)
            else:
                img = ImageGrab.grab()

            img.save(str(filepath))
            return {"success": True, "path": str(filepath)}
        except Exception as e:
            return {"success": False, "error": str(e)}


windows_engine = WindowsEngine()

__all__ = ["WindowsEngine", "windows_engine", "PYWINAUTO_AVAILABLE"]
