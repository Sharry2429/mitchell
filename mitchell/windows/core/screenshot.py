import ctypes
import ctypes.wintypes
import io
from typing import Any

from PIL import Image


# GDI structures
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", ctypes.wintypes.DWORD * 3),
    ]


try:
    import dxcam

    DXCAM_AVAILABLE = True
    _camera = None
except ImportError:
    DXCAM_AVAILABLE = False

from mitchell.windows.config import get_config

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Constants
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


def get_screen_size() -> tuple[int, int]:
    """Returns the primary screen width and height."""
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return width, height


def get_monitor_rects() -> list[tuple[int, int, int, int]]:
    """Returns a list of monitor rectangles: (left, top, right, bottom)."""
    monitors = []

    @ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL,
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(ctypes.wintypes.RECT),
        ctypes.wintypes.LPARAM,
    )
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        monitors.append((rect.left, rect.top, rect.right, rect.bottom))
        return True

    user32.EnumDisplayMonitors(None, None, callback, 0)
    return monitors


def capture_screen_gdi(region: tuple[int, int, int, int] | None = None) -> Any:
    """Captures the screen using GDI (ctypes)."""
    if region is None:
        left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    else:
        left, top, right, bottom = region
        width = right - left
        height = bottom - top

    hdesktop = user32.GetDesktopWindow()
    desktop_dc = user32.GetWindowDC(hdesktop)
    mem_dc = gdi32.CreateCompatibleDC(desktop_dc)

    screenshot_bmp = gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
    old_bmp = gdi32.SelectObject(mem_dc, screenshot_bmp)

    gdi32.BitBlt(mem_dc, 0, 0, width, height, desktop_dc, left, top, SRCCOPY)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # Top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB
    bmi.bmiHeader.biSizeImage = 0

    buffer = ctypes.create_string_buffer(width * height * 4)

    gdi32.GetDIBits(
        mem_dc, screenshot_bmp, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS
    )

    img = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
    # Convert RGBA to RGB (discard alpha channel)
    img = img.convert("RGB")

    # Cleanup
    gdi32.SelectObject(mem_dc, old_bmp)
    gdi32.DeleteObject(screenshot_bmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hdesktop, desktop_dc)

    return img


def capture_screen_dxcam(
    region: tuple[int, int, int, int] | None = None, monitor: int = 0
) -> Any:
    """Captures the screen using DXCam. Requires dxcam to be installed."""
    if not DXCAM_AVAILABLE:
        raise RuntimeError("DXCam is not installed or available.")

    global _camera
    if _camera is None or _camera.output_idx != monitor:
        if _camera is not None:
            _camera.stop()
            _camera = None
        _camera = dxcam.create(output_idx=monitor, output_color="RGB")

    frame = _camera.grab(region=region)
    if frame is None:
        # Fallback if frame failed (e.g. exclusive fullscreen issue)
        raise RuntimeError("DXCam failed to capture frame.")

    return Image.fromarray(frame)


def capture_screen(
    region: tuple[int, int, int, int] | None = None, monitor: int | None = None
) -> Any:
    """
    Captures the screen based on configuration (DXCam or GDI).
    Falls back to GDI if DXCam is configured but unavailable.
    """
    config = get_config()
    use_dxcam = (
        config.get("use_dxcam", False)
        if isinstance(config, dict)
        else getattr(config, "use_dxcam", False)
    )

    if use_dxcam and DXCAM_AVAILABLE:
        try:
            target_monitor = monitor if monitor is not None else 0
            return capture_screen_dxcam(region=region, monitor=target_monitor)
        except Exception:
            # Fallback to GDI if DXCam fails
            pass

    # GDI fallback or selection
    # If a specific monitor is requested and region is not provided, compute region for the monitor
    if monitor is not None and region is None:
        rects = get_monitor_rects()
        if 0 <= monitor < len(rects):
            region = rects[monitor]

    return capture_screen_gdi(region=region)


def save_screenshot(image: Any, path: str, format: str = "PNG") -> str:
    """Saves the screenshot to the specified path."""
    image.save(path, format=format)
    return path


def image_to_bytes(image: Any, format: str = "PNG") -> bytes:
    """Converts the screenshot Image to bytes."""
    with io.BytesIO() as bio:
        image.save(bio, format=format)
        return bio.getvalue()
