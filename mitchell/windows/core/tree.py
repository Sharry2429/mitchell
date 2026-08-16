"""UI Element Tree Walker — extract interactive elements from the screen."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging

from mitchell.windows.types import BoundingBox, UIElement

__all__ = [
    "find_elements_by_text",
    "find_elements_by_type",
    "get_element_at_point",
    "get_interactive_elements",
    "get_scrollable_elements",
    "walk_ui_tree",
]

logger = logging.getLogger("wincontrol.core.tree")

user32 = ctypes.windll.user32


def walk_ui_tree(
    hwnd: int | None = None,
    max_depth: int = 10,
    include_invisible: bool = False,
) -> list[UIElement]:
    """Walk the UI element tree and extract all elements.

    Args:
        hwnd: Window handle to walk. None for entire desktop.
        max_depth: Maximum tree depth to traverse.
        include_invisible: Include invisible elements.

    Returns:
        List of UIElement objects found.
    """
    elements: list[UIElement] = []
    label_counter = [0]

    def _get_child_windows(parent_hwnd: int) -> list[int]:
        """Enumerate child windows."""
        children: list[int] = []

        @ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        def callback(child_hwnd, lparam):
            children.append(child_hwnd)
            return True

        user32.EnumChildWindows(parent_hwnd, callback, 0)
        return children

    def _get_window_text(h: int) -> str:
        length = user32.GetWindowTextLengthW(h)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h, buf, length + 1)
        return buf.value

    def _get_class_name(h: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, buf, 256)
        return buf.value

    def _get_rect(h: int) -> tuple[int, int, int, int]:
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.wintypes.LONG),
                ("top", ctypes.wintypes.LONG),
                ("right", ctypes.wintypes.LONG),
                ("bottom", ctypes.wintypes.LONG),
            ]

        rect = RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        return (rect.left, rect.top, rect.right, rect.bottom)

    def _class_to_control_type(class_name: str) -> str:
        """Map Windows class names to control types."""
        mapping = {
            "Button": "Button",
            "Edit": "Edit",
            "Static": "Text",
            "ComboBox": "ComboBox",
            "ListBox": "List",
            "SysListView32": "List",
            "SysTreeView32": "Tree",
            "msctls_trackbar32": "Slider",
            "msctls_progress32": "ProgressBar",
            "SysTabControl32": "Tab",
            "ToolbarWindow32": "ToolBar",
            "tooltips_class32": "ToolTip",
            "msctls_statusbar32": "StatusBar",
            "RichEdit20W": "Edit",
            "RichEdit50W": "Edit",
            "RICHEDIT50W": "Edit",
            "Scintilla": "Edit",
            "SysHeader32": "Header",
            "ScrollBar": "ScrollBar",
            "MDIClient": "Pane",
        }
        for key, val in mapping.items():
            if key.lower() in class_name.lower():
                return val
        return "Custom"

    def _walk(h: int, depth: int, parent_name: str) -> None:
        if depth > max_depth:
            return

        if not include_invisible and not user32.IsWindowVisible(h):
            return

        text = _get_window_text(h)
        class_name = _get_class_name(h)
        control_type = _class_to_control_type(class_name)
        left, top, right, bottom = _get_rect(h)

        # Skip zero-sized elements
        if right <= left or bottom <= top:
            return

        label_counter[0] += 1
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2

        element = UIElement(
            label=label_counter[0],
            name=text,
            control_type=control_type,
            bounding_box=BoundingBox(left=left, top=top, right=right, bottom=bottom),
            center=(center_x, center_y),
            window_name=parent_name or text,
            is_enabled=bool(user32.IsWindowEnabled(h)),
            metadata={"class_name": class_name, "handle": h},
        )
        elements.append(element)

        # Recurse into children
        for child in _get_child_windows(h):
            _walk(child, depth + 1, parent_name or text)

    if hwnd is None:
        # Walk all top-level windows
        top_level: list[int] = []

        @ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        def enum_top(h, lp):
            if user32.IsWindowVisible(h):
                top_level.append(h)
            return True

        user32.EnumWindows(enum_top, 0)

        for h in top_level:
            _walk(h, 0, "")
    else:
        parent_text = _get_window_text(hwnd)
        _walk(hwnd, 0, parent_text)

    return elements


def get_interactive_elements(
    hwnd: int | None = None,
    max_depth: int = 8,
) -> list[UIElement]:
    """Get interactive UI elements (buttons, edits, links, etc.).

    Args:
        hwnd: Window handle. None for the foreground window.
        max_depth: Maximum depth to traverse.

    Returns:
        List of interactive UIElement objects.
    """
    if hwnd is None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return []

    all_elements = walk_ui_tree(hwnd, max_depth=max_depth)

    interactive_types = {
        "Button",
        "Edit",
        "ComboBox",
        "List",
        "Slider",
        "Tab",
        "Tree",
        "Hyperlink",
        "MenuItem",
        "CheckBox",
        "RadioButton",
        "ScrollBar",
    }

    return [el for el in all_elements if el.control_type in interactive_types]


def get_scrollable_elements(
    hwnd: int | None = None,
    max_depth: int = 8,
) -> list[UIElement]:
    """Get scrollable UI elements.

    Args:
        hwnd: Window handle. None for the foreground window.
        max_depth: Maximum depth to traverse.

    Returns:
        List of scrollable UIElement objects.
    """
    if hwnd is None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return []

    all_elements = walk_ui_tree(hwnd, max_depth=max_depth)
    scrollable_types = {"ScrollBar", "List", "Tree", "Edit"}

    return [el for el in all_elements if el.control_type in scrollable_types]


def find_elements_by_text(
    text: str,
    hwnd: int | None = None,
    case_sensitive: bool = False,
    max_depth: int = 8,
) -> list[UIElement]:
    """Find UI elements containing the specified text.

    Args:
        text: Text to search for.
        hwnd: Window handle. None for the foreground window.
        case_sensitive: Whether to match case.
        max_depth: Maximum depth to traverse.

    Returns:
        List of matching UIElement objects.
    """
    if hwnd is None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return []

    all_elements = walk_ui_tree(hwnd, max_depth=max_depth)

    if case_sensitive:
        return [el for el in all_elements if text in el.name]
    else:
        text_lower = text.lower()
        return [el for el in all_elements if text_lower in el.name.lower()]


def find_elements_by_type(
    control_type: str,
    hwnd: int | None = None,
    max_depth: int = 8,
) -> list[UIElement]:
    """Find UI elements of a specific control type.

    Args:
        control_type: Control type to search for (e.g., 'Button', 'Edit').
        hwnd: Window handle. None for the foreground window.
        max_depth: Maximum depth to traverse.

    Returns:
        List of matching UIElement objects.
    """
    if hwnd is None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return []

    all_elements = walk_ui_tree(hwnd, max_depth=max_depth)
    ct_lower = control_type.lower()
    return [el for el in all_elements if el.control_type.lower() == ct_lower]


def get_element_at_point(x: int, y: int) -> UIElement | None:
    """Get the UI element at a specific screen point.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        UIElement at the point, or None.
    """
    hwnd = user32.WindowFromPoint(ctypes.wintypes.POINT(x, y))
    if not hwnd:
        return None

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.wintypes.LONG),
            ("top", ctypes.wintypes.LONG),
            ("right", ctypes.wintypes.LONG),
            ("bottom", ctypes.wintypes.LONG),
        ]

    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    length = user32.GetWindowTextLengthW(hwnd)
    buf = (
        ctypes.create_unicode_buffer(length + 1)
        if length > 0
        else ctypes.create_unicode_buffer(1)
    )
    user32.GetWindowTextW(hwnd, buf, length + 1)

    class_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buf, 256)

    return UIElement(
        label=0,
        name=buf.value,
        control_type=class_buf.value,
        bounding_box=BoundingBox(
            left=rect.left, top=rect.top, right=rect.right, bottom=rect.bottom
        ),
        center=(x, y),
        window_name=buf.value,
        is_enabled=bool(user32.IsWindowEnabled(hwnd)),
        metadata={"class_name": class_buf.value, "handle": hwnd},
    )
