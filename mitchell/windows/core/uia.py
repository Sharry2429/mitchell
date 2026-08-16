"""UI Automation wrapper — simplified UIA access via comtypes."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
from typing import Any

__all__ = [
    "find_element_by_automation_id",
    "find_element_by_name",
    "get_cursor_pos",
    "get_desktop_element",
    "get_element_bounding_rect",
    "get_element_children",
    "get_element_control_type",
    "get_element_name",
    "get_focused_element",
    "get_foreground_window",
    "is_iconic",
    "is_window_visible",
    "is_zoomed",
    "send_keys",
    "set_cursor_pos",
    "set_foreground_window",
]

logger = logging.getLogger("wincontrol.core.uia")

# ─── Win32 API bindings ─────────────────────────────────────────────────────

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.wintypes.LONG),
        ("top", ctypes.wintypes.LONG),
        ("right", ctypes.wintypes.LONG),
        ("bottom", ctypes.wintypes.LONG),
    ]


def is_iconic(hwnd: int) -> bool:
    """Check if window is minimized."""
    return bool(user32.IsIconic(hwnd))


def is_zoomed(hwnd: int) -> bool:
    """Check if window is maximized."""
    return bool(user32.IsZoomed(hwnd))


def is_window_visible(hwnd: int) -> bool:
    """Check if window is visible."""
    return bool(user32.IsWindowVisible(hwnd))


def get_cursor_pos() -> tuple[int, int]:
    """Get current cursor position."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def set_cursor_pos(x: int, y: int) -> bool:
    """Set cursor position."""
    return bool(user32.SetCursorPos(x, y))


def get_foreground_window() -> int:
    """Get handle of the foreground window."""
    return user32.GetForegroundWindow()


def set_foreground_window(hwnd: int) -> bool:
    """Bring window to foreground."""
    # AllowSetForegroundWindow trick
    user32.AllowSetForegroundWindow(ctypes.wintypes.DWORD(-1))

    if is_iconic(hwnd):
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)

    return bool(user32.SetForegroundWindow(hwnd))


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """Get window rectangle (left, top, right, bottom)."""
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def get_window_text(hwnd: int) -> str:
    """Get window title text."""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_class_name(hwnd: int) -> str:
    """Get window class name."""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def send_keys(text: str) -> None:
    """Send keystrokes using SendInput with Unicode events.

    This handles plain text. For special keys, use the input module.
    """
    from mitchell.windows.ui import type_text

    type_text(text)


# ─── UIA via comtypes (lazy initialization) ─────────────────────────────────

_uia_client = None


def _get_uia():
    """Lazily initialize UI Automation client."""
    global _uia_client
    if _uia_client is not None:
        return _uia_client

    try:
        import comtypes
        import comtypes.client

        # Create UIAutomation instance
        comtypes.CoInitialize()
        _uia_client = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",  # CUIAutomation CLSID
            interface=None,
        )
        logger.info("UI Automation initialized via comtypes")
        return _uia_client
    except Exception as e:
        logger.warning(f"Failed to initialize UI Automation: {e}")
        return None


def get_desktop_element() -> Any:
    """Get the root desktop UI Automation element."""
    uia = _get_uia()
    if uia is None:
        return None
    try:
        return uia.GetRootElement()
    except Exception as e:
        logger.warning(f"Failed to get desktop element: {e}")
        return None


def get_focused_element() -> Any:
    """Get the currently focused UI Automation element."""
    uia = _get_uia()
    if uia is None:
        return None
    try:
        return uia.GetFocusedElement()
    except Exception as e:
        logger.warning(f"Failed to get focused element: {e}")
        return None


def get_element_name(element: Any) -> str:
    """Get the Name property of a UIA element."""
    try:
        return element.CurrentName or ""
    except Exception:
        return ""


def get_element_control_type(element: Any) -> str:
    """Get the control type name of a UIA element."""
    _CONTROL_TYPE_NAMES = {
        50000: "Button",
        50001: "Calendar",
        50002: "CheckBox",
        50003: "ComboBox",
        50004: "Edit",
        50005: "Hyperlink",
        50006: "Image",
        50007: "ListItem",
        50008: "List",
        50009: "Menu",
        50010: "MenuBar",
        50011: "MenuItem",
        50012: "ProgressBar",
        50013: "RadioButton",
        50014: "ScrollBar",
        50015: "Slider",
        50016: "Spinner",
        50017: "StatusBar",
        50018: "Tab",
        50019: "TabItem",
        50020: "Text",
        50021: "ToolBar",
        50022: "ToolTip",
        50023: "Tree",
        50024: "TreeItem",
        50025: "Custom",
        50026: "Group",
        50027: "Thumb",
        50028: "DataGrid",
        50029: "DataItem",
        50030: "Document",
        50031: "SplitButton",
        50032: "Window",
        50033: "Pane",
        50034: "Header",
        50035: "HeaderItem",
        50036: "Table",
        50037: "TitleBar",
        50038: "Separator",
    }
    try:
        ct_id = element.CurrentControlType
        return _CONTROL_TYPE_NAMES.get(ct_id, f"Unknown({ct_id})")
    except Exception:
        return "Unknown"


def get_element_bounding_rect(element: Any) -> tuple[int, int, int, int]:
    """Get the bounding rectangle of a UIA element (left, top, right, bottom)."""
    try:
        rect = element.CurrentBoundingRectangle
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        return (0, 0, 0, 0)


def get_element_children(element: Any) -> list[Any]:
    """Get child elements of a UIA element."""
    uia = _get_uia()
    if uia is None or element is None:
        return []
    try:
        condition = uia.CreateTrueCondition()
        children = element.FindAll(1, condition)  # TreeScope_Children = 1
        result = []
        for i in range(children.Length):
            result.append(children.GetElement(i))
        return result
    except Exception as e:
        logger.warning(f"Failed to get element children: {e}")
        return []


def find_element_by_name(name: str, root: Any = None) -> Any:
    """Find a UI element by name under the given root (or desktop)."""
    uia = _get_uia()
    if uia is None:
        return None

    if root is None:
        root = get_desktop_element()
    if root is None:
        return None

    try:
        # UIA_NamePropertyId = 30005
        condition = uia.CreatePropertyCondition(30005, name)
        element = root.FindFirst(4, condition)  # TreeScope_Descendants = 4
        return element
    except Exception as e:
        logger.warning(f"Failed to find element by name '{name}': {e}")
        return None


def find_element_by_automation_id(automation_id: str, root: Any = None) -> Any:
    """Find a UI element by AutomationId under the given root (or desktop)."""
    uia = _get_uia()
    if uia is None:
        return None

    if root is None:
        root = get_desktop_element()
    if root is None:
        return None

    try:
        # UIA_AutomationIdPropertyId = 30011
        condition = uia.CreatePropertyCondition(30011, automation_id)
        element = root.FindFirst(4, condition)  # TreeScope_Descendants = 4
        return element
    except Exception as e:
        logger.warning(
            f"Failed to find element by automation ID '{automation_id}': {e}"
        )
        return None


def enumerate_windows() -> list[int]:
    """Enumerate all top-level windows and return their handles."""
    handles: list[int] = []

    @ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    def enum_callback(hwnd, lparam):
        handles.append(hwnd)
        return True

    user32.EnumWindows(enum_callback, 0)
    return handles


def enumerate_child_windows(parent_hwnd: int) -> list[int]:
    """Enumerate child windows of a parent window."""
    handles: list[int] = []

    @ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    def enum_callback(hwnd, lparam):
        handles.append(hwnd)
        return True

    user32.EnumChildWindows(parent_hwnd, enum_callback, 0)
    return handles


def get_window_process_id(hwnd: int) -> int:
    """Get the process ID that owns a window."""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value
