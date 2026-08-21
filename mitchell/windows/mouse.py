"""Desktop human-like mouse movement and click driver using Windows API."""

import asyncio
import ctypes
import math
import random
import time
from typing import Dict, Optional, Tuple

from mitchell.browser.mouse import generate_bezier_curve

# Win32 structures and constants
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0009
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


class DesktopMouse:
    """Controls OS-level mouse pointer with realistic human trajectories and jitter."""

    def __init__(self) -> None:
        self.user32 = getattr(ctypes, "windll", None)
        if self.user32:
            self.user32 = self.user32.user32

    def get_position(self) -> Tuple[int, int]:
        """Get current physical cursor coordinates."""
        if not self.user32:
            return (0, 0)
        pt = POINT()
        self.user32.GetCursorPos(ctypes.byref(pt))
        return (int(pt.x), int(pt.y))

    def set_position(self, x: int, y: int) -> None:
        """Set physical cursor coordinates."""
        if self.user32:
            self.user32.SetCursorPos(int(x), int(y))

    def move_to(
        self,
        target_x: int,
        target_y: int,
        speed: str = "normal",
    ) -> None:
        """Move cursor to target coordinates along a smooth Bezier trajectory."""
        start_x, start_y = self.get_position()
        dist = math.hypot(target_x - start_x, target_y - start_y)
        if dist < 3:
            self.set_position(target_x, target_y)
            return

        speed_map = {"fast": (15, 0.005), "normal": (30, 0.01), "slow": (45, 0.015)}
        steps, base_delay = speed_map.get(speed, (30, 0.01))

        # Overshoot on longer jumps
        if dist > 180 and random.random() < 0.35:
            overshoot_factor = random.uniform(1.03, 1.07)
            ox = start_x + (target_x - start_x) * overshoot_factor
            oy = start_y + (target_y - start_y) * overshoot_factor
            curve1 = generate_bezier_curve((start_x, start_y), (ox, oy), num_points=int(steps * 0.75))
            for px, py in curve1:
                self.set_position(px, py)
                time.sleep(base_delay)
            time.sleep(random.uniform(0.03, 0.06))
            curve2 = generate_bezier_curve((ox, oy), (target_x, target_y), num_points=int(steps * 0.35))
            for px, py in curve2:
                self.set_position(px, py)
                time.sleep(base_delay * 0.8)
        else:
            curve = generate_bezier_curve((start_x, start_y), (target_x, target_y), num_points=steps)
            for px, py in curve:
                self.set_position(px, py)
                time.sleep(base_delay)

        self.set_position(target_x, target_y)

    def click(self, button: str = "left") -> None:
        """Perform mouse click with randomized dwell timing."""
        if not self.user32:
            return

        time.sleep(random.uniform(0.04, 0.09))
        if button == "left":
            self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.06, 0.12))
            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == "right":
            self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.06, 0.12))
            self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        elif button == "middle":
            self.user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.06, 0.12))
            self.user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)

        time.sleep(random.uniform(0.03, 0.08))

    def click_rect(
        self,
        rect: Dict[str, int],
        button: str = "left",
        speed: str = "normal",
    ) -> None:
        """Move human-like to an element rectangle and click with randomized offset."""
        left = rect.get("left", 0)
        top = rect.get("top", 0)
        width = max(2, rect.get("width", 20))
        height = max(2, rect.get("height", 20))

        # Target inner 70% of rectangle
        margin_x = width * 0.15
        margin_y = height * 0.15
        tx = int(left + margin_x + random.random() * max(1, width - 2 * margin_x))
        ty = int(top + margin_y + random.random() * max(1, height - 2 * margin_y))

        self.move_to(tx, ty, speed=speed)
        self.click(button=button)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        """Drag mouse from start to end coordinates."""
        if not self.user32:
            return
        self.move_to(start_x, start_y)
        time.sleep(0.05)
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.08)
        self.move_to(end_x, end_y, speed="slow")
        time.sleep(0.06)
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.05)


desktop_mouse = DesktopMouse()

__all__ = ["DesktopMouse", "desktop_mouse"]
