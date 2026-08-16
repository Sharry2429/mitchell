import ctypes
import time
from ctypes import wintypes

import psutil
import win32clipboard
import win32con
import win32gui
import win32process
from fuzzywuzzy import process

from mitchell.windows.core.powershell import execute
from mitchell.windows.core.screenshot import (
    capture_screen,
    image_to_bytes,
    save_screenshot,
)
from mitchell.windows.types import (
    BoundingBox,
    DesktopState,
    DisplayInfo,
    ScreenshotResult,
    UIElement,
    Window,
    WindowStatus,
)

# --- desktop.py ---


__all__ = [
    "find_element",
    "get_active_window",
    "get_cursor_position",
    "get_displays",
    "get_ui_elements",
    "get_window_by_title",
    "get_windows",
    "screenshot",
    "snapshot",
]

user32 = ctypes.windll.user32


def snapshot(use_vision: bool = False, use_annotation: bool = True) -> DesktopState:
    windows = get_windows()
    active_window = get_active_window()
    displays = get_displays()
    cursor = get_cursor_position()
    ui_elements = get_ui_elements()

    screen_res = None
    if use_vision:
        screen_res = screenshot()

    return DesktopState(
        windows=windows,
        active_window_handle=active_window.handle if active_window else None,
        cursor_position=cursor,
        displays=displays,
        ui_elements=ui_elements,
        screenshot=screen_res,
    )


def screenshot(
    region: tuple[int, int, int, int] | None = None, save_path: str | None = None
) -> ScreenshotResult:
    img = capture_screen(region)
    data = image_to_bytes(img)
    if save_path:
        save_screenshot(img, save_path)
    return ScreenshotResult(data=data, region=region)


def _get_window_status(hwnd: int) -> WindowStatus:
    if user32.IsIconic(hwnd):
        return WindowStatus.MINIMIZED
    if user32.IsZoomed(hwnd):
        return WindowStatus.MAXIMIZED
    return WindowStatus.NORMAL


def _get_process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "Unknown"


def _create_window_obj(hwnd: int) -> Window | None:
    if not win32gui.IsWindowVisible(hwnd):
        return None

    title = win32gui.GetWindowText(hwnd)
    if not title:
        return None

    rect = win32gui.GetWindowRect(hwnd)
    bbox = BoundingBox(left=rect[0], top=rect[1], right=rect[2], bottom=rect[3])

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_name = _get_process_name(pid)
    except Exception:
        process_name = "Unknown"
        pid = 0

    status = _get_window_status(hwnd)

    return Window(
        handle=hwnd,
        title=title,
        process_name=process_name,
        process_id=pid,
        bounds=bbox,
        status=status,
        is_active=(hwnd == win32gui.GetForegroundWindow()),
    )


def get_windows() -> list[Window]:
    windows: list[Window] = []

    def enum_windows_proc(hwnd, lParam):
        win = _create_window_obj(hwnd)
        if win:
            windows.append(win)
        return True

    try:
        win32gui.EnumWindows(enum_windows_proc, 0)
    except Exception:
        pass

    return windows


def get_active_window() -> Window | None:
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            return _create_window_obj(hwnd)
    except Exception:
        pass
    return None


def get_cursor_position() -> tuple[int, int]:
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def get_displays() -> list[DisplayInfo]:
    displays: list[DisplayInfo] = []

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(RECT),
        ctypes.c_void_p,
    )

    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
            is_primary = bool(mi.dwFlags & 1)
            bounds = BoundingBox(
                left=mi.rcMonitor.left,
                top=mi.rcMonitor.top,
                right=mi.rcMonitor.right,
                bottom=mi.rcMonitor.bottom,
            )
            work_area = BoundingBox(
                left=mi.rcWork.left,
                top=mi.rcWork.top,
                right=mi.rcWork.right,
                bottom=mi.rcWork.bottom,
            )
            displays.append(
                DisplayInfo(
                    handle=hMonitor,
                    is_primary=is_primary,
                    bounds=bounds,
                    work_area=work_area,
                )
            )
        return True

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
    return displays


def get_ui_elements(window_handle: int | None = None) -> list[UIElement]:
    elements: list[UIElement] = []

    def enum_child_proc(hwnd, lParam):
        if not win32gui.IsWindowVisible(hwnd):
            return True

        rect = win32gui.GetWindowRect(hwnd)
        bbox = BoundingBox(left=rect[0], top=rect[1], right=rect[2], bottom=rect[3])

        try:
            text = win32gui.GetWindowText(hwnd)
        except Exception:
            text = ""

        try:
            class_name = win32gui.GetClassName(hwnd)
        except Exception:
            class_name = ""

        elements.append(
            UIElement(
                handle=hwnd,
                text=text,
                control_type=class_name,
                bounds=bbox,
                is_visible=True,
            )
        )
        return True

    try:
        if window_handle is None:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                win32gui.EnumChildWindows(hwnd, enum_child_proc, 0)
        else:
            win32gui.EnumChildWindows(window_handle, enum_child_proc, 0)
    except Exception:
        pass

    return elements


def find_element(text: str = "", control_type: str = "") -> UIElement | None:
    elements = get_ui_elements()

    for el in elements:
        match_text = True
        if text:
            match_text = (text.lower() in el.text.lower()) if el.text else False

        match_ctype = True
        if control_type:
            match_ctype = (
                (control_type.lower() in el.control_type.lower())
                if el.control_type
                else False
            )

        if text and control_type:
            if match_text and match_ctype:
                return el
        elif text and match_text or control_type and match_ctype:
            return el

    return None


def get_window_by_title(title: str, fuzzy: bool = True) -> Window | None:
    windows = get_windows()
    if not windows:
        return None

    if not fuzzy:
        for w in windows:
            if w.title and title.lower() in w.title.lower():
                return w
        return None

    titles = {w.handle: w.title for w in windows if w.title}
    if not titles:
        return None

    match = process.extractOne(title, titles)
    if match and match[1] >= 70:
        handle = match[2]
        for w in windows:
            if w.handle == handle:
                return w

    return None


# --- input.py ---


__all__ = [
    "click",
    "double_click",
    "drag",
    "get_mouse_position",
    "hotkey",
    "key_down",
    "key_up",
    "middle_click",
    "move_mouse",
    "press_key",
    "right_click",
    "scroll",
    "type_text",
    "wait",
    "wait_for",
]

user32 = ctypes.windll.user32

# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

# Keyboard Event Flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008


# CTypes Structures
class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class INPUT_UNION(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _fields_ = (("type", wintypes.DWORD), ("union", INPUT_UNION))


# Key mappings
KEY_MAPPING = {
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B,
    "enter": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "space": 0x20,
    "capslock": 0x14,
    "numlock": 0x90,
    "printscreen": 0x2C,
    "insert": 0x2D,
}

# Add F1-F12
for i in range(1, 13):
    KEY_MAPPING[f"f{i}"] = 0x70 + i - 1


def _send_input(inputs):
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.c_int(ctypes.sizeof(INPUT))
    return user32.SendInput(nInputs, pInputs, cbSize)


def get_mouse_position() -> tuple[int, int]:
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _create_mouse_input(flags, dx=0, dy=0, data=0):
    mi = MOUSEINPUT(dx, dy, data, flags, 0, None)
    return INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))


def _do_click(button: str, down: bool):
    flags = 0
    if button == "left":
        flags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    elif button == "right":
        flags = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
    elif button == "middle":
        flags = MOUSEEVENTF_MIDDLEDOWN if down else MOUSEEVENTF_MIDDLEUP

    if flags:
        _send_input([_create_mouse_input(flags)])


def move_mouse(x: int, y: int, duration: float = 0.0) -> None:
    if duration <= 0:
        user32.SetCursorPos(x, y)
    else:
        start_x, start_y = get_mouse_position()
        dx = x - start_x
        dy = y - start_y

        steps = max(1, int(duration * 60))
        sleep_time = duration / steps

        for i in range(1, steps + 1):
            t = i / steps
            cx = start_x + int(dx * t)
            cy = start_y + int(dy * t)
            user32.SetCursorPos(cx, cy)
            time.sleep(sleep_time)
        user32.SetCursorPos(x, y)


def click(x: int, y: int, button: str = "left", count: int = 1) -> None:
    move_mouse(x, y)
    for _ in range(count):
        _do_click(button, True)
        _do_click(button, False)
        if count > 1:
            time.sleep(0.05)


def double_click(x: int, y: int) -> None:
    click(x, y, button="left", count=2)


def right_click(x: int, y: int) -> None:
    click(x, y, button="right", count=1)


def middle_click(x: int, y: int) -> None:
    click(x, y, button="middle", count=1)


def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.5,
) -> None:
    move_mouse(start_x, start_y)
    _do_click(button, True)
    move_mouse(end_x, end_y, duration)
    _do_click(button, False)


def scroll(x: int, y: int, amount: int, direction: str = "vertical") -> None:
    move_mouse(x, y)
    flag = MOUSEEVENTF_WHEEL if direction == "vertical" else MOUSEEVENTF_HWHEEL
    # A wheel click is defined as WHEEL_DELTA, which is 120.
    # The dwData parameter can be positive or negative.
    _send_input([_create_mouse_input(flag, data=amount)])


def _create_keyboard_input(vk, scan, flags):
    ki = KEYBDINPUT(vk, scan, flags, 0, None)
    return INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki))


def key_down(key: str) -> None:
    key_lower = key.lower()
    if len(key_lower) == 1:
        vk = user32.VkKeyScanW(ord(key_lower)) & 0xFF
        _send_input([_create_keyboard_input(vk, 0, 0)])
    elif key_lower in KEY_MAPPING:
        vk = KEY_MAPPING[key_lower]
        _send_input([_create_keyboard_input(vk, 0, 0)])


def key_up(key: str) -> None:
    key_lower = key.lower()
    if len(key_lower) == 1:
        vk = user32.VkKeyScanW(ord(key_lower)) & 0xFF
        _send_input([_create_keyboard_input(vk, 0, KEYEVENTF_KEYUP)])
    elif key_lower in KEY_MAPPING:
        vk = KEY_MAPPING[key_lower]
        _send_input([_create_keyboard_input(vk, 0, KEYEVENTF_KEYUP)])


def press_key(key: str) -> None:
    key_down(key)
    time.sleep(0.01)
    key_up(key)


def hotkey(keys: list[str]) -> None:
    """Presses a combination of keys (e.g. ['ctrl', 'c'])."""
    for k in keys:
        key_down(k)
        time.sleep(0.01)
    for k in reversed(keys):
        key_up(k)
        time.sleep(0.01)


def type_text(text: str, interval: float = 0.0) -> None:
    for char in text:
        inputs = []
        scan_code = ord(char)
        ki_down = KEYBDINPUT(0, scan_code, KEYEVENTF_UNICODE, 0, None)
        inputs.append(INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_down)))
        ki_up = KEYBDINPUT(0, scan_code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
        inputs.append(INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_up)))

        _send_input(inputs)

        if interval > 0:
            time.sleep(interval)


def wait(seconds: float) -> None:
    time.sleep(seconds)


def wait_for(
    condition: str,
    text: str | None = None,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> bool:
    if condition == "text_exists":
        from mitchell.windows.ocr import get_desktop_text

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_text = get_desktop_text()
            if text and text in current_text:
                return True
            time.sleep(poll_interval)
        return False
    elif condition == "window_active":
        from mitchell.windows.window import get_active_window_title

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_title = get_active_window_title()
            if text and text in current_title:
                return True
            time.sleep(poll_interval)
        return False
    elif condition == "element_exists":
        from mitchell.windows.uia import element_exists

        start_time = time.time()
        while time.time() - start_time < timeout:
            if element_exists(text):
                return True
            time.sleep(poll_interval)
        return False

    return False


# --- clipboard.py ---
"""
Clipboard operations using ctypes/win32clipboard.
"""


__all__ = [
    "clear_clipboard",
    "get_clipboard",
    "get_clipboard_formats",
    "get_clipboard_image",
    "set_clipboard",
    "set_clipboard_image",
]


def get_clipboard() -> str:
    """Get text from clipboard."""
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            return data
        return ""
    finally:
        win32clipboard.CloseClipboard()


def set_clipboard(text: str) -> None:
    """Set clipboard text."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def get_clipboard_image() -> bytes | None:
    """Get image from clipboard as PNG bytes."""
    # Note: Returning raw CF_DIB bytes. Converting raw DIB to PNG without Pillow is non-trivial.
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
            data = win32clipboard.GetClipboardData(win32con.CF_DIB)
            return data
        return None
    finally:
        win32clipboard.CloseClipboard()


def set_clipboard_image(image_path: str) -> None:
    """Set clipboard image from file."""
    # Note: Expects BMP path typically when using DIB
    with open(image_path, "rb") as f:
        image_data = f.read()

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        # In a complete implementation, this would require converting the image to CF_DIB/CF_BITMAP
        # For the scope of this module, we set it as generic data or DIB if it is one.
        win32clipboard.SetClipboardData(
            win32con.CF_DIB, image_data[14:]
        )  # Skip BMP header if assuming it's BMP
    finally:
        win32clipboard.CloseClipboard()


def clear_clipboard() -> None:
    """Clear clipboard contents."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
    finally:
        win32clipboard.CloseClipboard()


def get_clipboard_formats() -> list[str]:
    """List available clipboard formats."""
    formats = []
    win32clipboard.OpenClipboard()
    try:
        f = win32clipboard.EnumClipboardFormats(0)
        while f:
            formats.append(str(f))
            f = win32clipboard.EnumClipboardFormats(f)
    finally:
        win32clipboard.CloseClipboard()
    return formats


# --- notification.py ---
"""
Windows toast notifications.
"""


__all__ = ["send_alert", "send_notification"]


def send_notification(
    title: str, body: str, icon_path: str | None = None, duration: str = "short"
) -> bool:
    """Send a Windows toast notification."""
    duration_ms = 3000 if duration == "short" else 10000

    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    """

    if icon_path:
        ps_script += (
            f"\n    $notify.Icon = New-Object System.Drawing.Icon('{icon_path}')"
        )

    ps_script += f"""
    $notify.Visible = $True
    $notify.ShowBalloonTip({duration_ms}, '{title}', '{body}', [System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -Milliseconds {duration_ms + 1000}
    $notify.Dispose()
    """

    try:
        execute(ps_script)
        return True
    except Exception:
        return False


def send_alert(message: str, title: str = "WinControl") -> bool:
    """Show a MessageBox alert."""
    MB_OK = 0x0
    MB_ICONINFORMATION = 0x40
    MB_TOPMOST = 0x40000

    try:
        ctypes.windll.user32.MessageBoxW(
            0, message, title, MB_OK | MB_ICONINFORMATION | MB_TOPMOST
        )
        return True
    except Exception:
        return False
