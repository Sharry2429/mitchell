"""Human-like mouse movement and typing simulation for Playwright."""

import asyncio
import math
import random
from typing import Any, List, Optional, Tuple


def _bezier_point(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """Calculate single coordinate on a cubic Bezier curve."""
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t ** 2 * p2
        + t ** 3 * p3
    )


def generate_bezier_curve(
    start: Tuple[float, float],
    end: Tuple[float, float],
    num_points: int = 40,
    deviation: float = 0.3,
) -> List[Tuple[float, float]]:
    """Generate a realistic curved trajectory using cubic Bezier curves with jitter."""
    x0, y0 = start
    x3, y3 = end

    dx = x3 - x0
    dy = y3 - y0
    dist = math.hypot(dx, dy)

    if dist < 5:
        return [start, end]

    # Normal vector for perpendicular offset
    nx = -dy / dist
    ny = dx / dist

    # Random control point offsets
    offset1 = (random.random() - 0.5) * 2 * deviation * dist
    offset2 = (random.random() - 0.5) * 2 * deviation * dist

    p1_x = x0 + dx * 0.25 + nx * offset1
    p1_y = y0 + dy * 0.25 + ny * offset1

    p2_x = x0 + dx * 0.75 + nx * offset2
    p2_y = y0 + dy * 0.75 + ny * offset2

    points: List[Tuple[float, float]] = []

    # Non-linear time distribution (accelerate then decelerate)
    for i in range(num_points):
        step = i / (num_points - 1)
        # Ease in-out shaping
        t = math.sin(step * math.pi / 2) if step < 0.5 else 1 - math.cos(step * math.pi / 2)
        # Blend linear and ease
        t = 0.5 * (step + t)

        bx = _bezier_point(x0, p1_x, p2_x, x3, t)
        by = _bezier_point(y0, p1_y, p2_y, y3, t)

        # Subtle micro-jitter along trajectory
        jitter_x = (random.random() - 0.5) * min(2.0, dist * 0.01)
        jitter_y = (random.random() - 0.5) * min(2.0, dist * 0.01)

        points.append((bx + jitter_x, by + jitter_y))

    return points


class HumanMouse:
    """Human-like mouse movement and interaction driver."""

    def __init__(self) -> None:
        self.current_x: float = random.uniform(200, 600)
        self.current_y: float = random.uniform(200, 400)

    async def move_to(
        self,
        page: Any,
        target_x: float,
        target_y: float,
        speed: str = "normal",
    ) -> None:
        """Smoothly move mouse from current position to target coordinates."""
        # 30% chance of overshoot on longer distances
        dist = math.hypot(target_x - self.current_x, target_y - self.current_y)
        should_overshoot = dist > 150 and random.random() < 0.3

        if should_overshoot:
            overshoot_factor = random.uniform(1.03, 1.08)
            ox = self.current_x + (target_x - self.current_x) * overshoot_factor
            oy = self.current_y + (target_y - self.current_y) * overshoot_factor
            await self._execute_trajectory(page, ox, oy, speed=speed)
            # Corrective movement
            await asyncio.sleep(random.uniform(0.04, 0.08))
            await self._execute_trajectory(page, target_x, target_y, speed="fast")
        else:
            await self._execute_trajectory(page, target_x, target_y, speed=speed)

        self.current_x = target_x
        self.current_y = target_y

    async def _execute_trajectory(
        self,
        page: Any,
        target_x: float,
        target_y: float,
        speed: str = "normal",
    ) -> None:
        """Execute Bezier curve mouse movement along steps."""
        speed_map = {"fast": (15, 0.005), "normal": (30, 0.012), "slow": (50, 0.02)}
        steps, delay = speed_map.get(speed, (30, 0.012))

        points = generate_bezier_curve(
            (self.current_x, self.current_y),
            (target_x, target_y),
            num_points=steps,
        )

        for px, py in points:
            try:
                await page.mouse.move(px, py)
            except Exception:
                pass
            await asyncio.sleep(delay + random.uniform(-0.002, 0.004))

    async def click_element(
        self,
        page: Any,
        selector_or_locator: Any,
        timeout: int = 10000,
    ) -> bool:
        """Move human-like to an element and click with random offset and dwell time."""
        try:
            if isinstance(selector_or_locator, str):
                locator = page.locator(selector_or_locator).first
            else:
                locator = selector_or_locator

            await locator.wait_for(state="visible", timeout=timeout)
            box = await locator.bounding_box()
            if not box:
                return False

            # Target position with randomized offset inside the inner 70% of element
            margin_x = box["width"] * 0.15
            margin_y = box["height"] * 0.15
            tx = box["x"] + margin_x + random.random() * max(1, box["width"] - 2 * margin_x)
            ty = box["y"] + margin_y + random.random() * max(1, box["height"] - 2 * margin_y)

            await self.move_to(page, tx, ty)

            # Pre-click dwell time
            await asyncio.sleep(random.uniform(0.04, 0.12))
            await page.mouse.down()
            # Click duration
            await asyncio.sleep(random.uniform(0.06, 0.14))
            await page.mouse.up()
            # Post-click pause
            await asyncio.sleep(random.uniform(0.05, 0.15))
            return True
        except Exception:
            return False

    async def type_text(
        self,
        page: Any,
        selector_or_locator: Any,
        text: str,
        clear_first: bool = True,
    ) -> bool:
        """Click input element and type text with realistic keystroke delays."""
        clicked = await self.click_element(page, selector_or_locator)
        if not clicked:
            return False

        if clear_first:
            try:
                await page.keyboard.press("Control+A")
                await asyncio.sleep(0.05)
                await page.keyboard.press("Backspace")
                await asyncio.sleep(0.08)
            except Exception:
                pass

        for char in text:
            await page.keyboard.type(char)
            # Randomized keystroke timing with occasional micro-pauses
            delay = random.uniform(0.04, 0.16)
            if char in (" ", ".", ",", "-", "@"):
                delay += random.uniform(0.1, 0.25)
            await asyncio.sleep(delay)

        return True


human_mouse = HumanMouse()

__all__ = ["HumanMouse", "human_mouse", "generate_bezier_curve"]
