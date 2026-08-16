import base64
import io
import os

import requests
from PIL import Image

from mitchell.android import adb
from mitchell.android.hardware import grab_frame
from mitchell.core.audit import log_action
from mitchell.core.errors import SystemMCPError
from mitchell.core.result import MCPResult


def tap(x: int, y: int) -> MCPResult:
    log_action("input", "tap", {"x": x, "y": y}, {})
    try:
        adb.shell(["input", "tap", str(x), str(y)])
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def swipe(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> MCPResult:
    log_action(
        "input",
        "swipe",
        {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration},
        {},
    )
    try:
        ms = int(duration * 1000)
        adb.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(ms)])
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def long_press(x: int, y: int, duration: float = 1.0) -> MCPResult:
    log_action("input", "long_press", {"x": x, "y": y, "duration": duration}, {})
    try:
        ms = int(duration * 1000)
        # Swipe in place acts as long press
        adb.shell(["input", "swipe", str(x), str(y), str(x), str(y), str(ms)])
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def type_text(text: str) -> MCPResult:
    log_action("input", "type_text", {"text_len": len(text)}, {})
    try:
        adb.shell(["input", "text", text])
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def key_event(keycode: str) -> MCPResult:
    log_action("input", "key_event", {"keycode": keycode}, {})
    try:
        adb.shell(["input", "keyevent", keycode])
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def analyze_screen(prompt: str) -> MCPResult:
    """
    Captures the current Android screen and sends it to the UI-TARS vision model
    along with the prompt. Returns actionable coordinates or insights based on visual context.
    """
    try:
        api_key = os.environ.get("AICREDITS_API_KEY")
        if not api_key:
            return MCPResult.fail("AICREDITS_API_KEY not found in environment.")

        frame_res = grab_frame()
        if not frame_res.success:
            return frame_res

        img = frame_res.data

        # Compress and resize the image for much faster API uploads
        if isinstance(img, Image.Image):
            img.thumbnail((800, 1600), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=65)
            image_bytes = buf.getvalue()
        else:
            image_bytes = img if isinstance(img, bytes) else bytes(img)

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "bytedance/ui-tars-1.5-7b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
        }

        response = requests.post(
            "https://api.aicredits.in/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        response_data = response.json()
        analysis = response_data["choices"][0]["message"]["content"]

        return MCPResult.success(
            {"analysis": analysis, "image_size_bytes": len(image_bytes)}
        )
    except Exception as e:
        return MCPResult.fail(str(e))
