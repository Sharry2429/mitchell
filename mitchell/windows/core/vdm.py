"""Virtual Desktop Manager — enumerate and manage Windows virtual desktops."""

from __future__ import annotations

import logging

__all__ = [
    "get_all_desktops",
    "get_current_desktop",
    "get_desktop_count",
    "is_window_on_current_desktop",
    "move_window_to_desktop",
    "switch_desktop",
]

logger = logging.getLogger("wincontrol.core.vdm")


def get_current_desktop() -> dict[str, str]:
    """Get the current virtual desktop info.

    Returns:
        Dict with 'id' and 'name' of the current desktop.
    """
    try:
        from pyvda import VirtualDesktop

        desktop = VirtualDesktop.current()
        return {
            "id": str(desktop.id),
            "name": desktop.name if desktop.name else f"Desktop {desktop.number}",
        }
    except Exception as e:
        logger.warning(f"Failed to get current desktop via pyvda: {e}")
        return {"id": "00000000-0000-0000-0000-000000000000", "name": "Desktop 1"}


def get_all_desktops() -> list[dict[str, str]]:
    """Get all virtual desktops.

    Returns:
        List of dicts with 'id' and 'name' for each desktop.
    """
    try:
        from pyvda import get_virtual_desktops

        desktops = get_virtual_desktops()
        return [
            {"id": str(d.id), "name": d.name if d.name else f"Desktop {d.number}"}
            for d in desktops
        ]
    except Exception as e:
        logger.warning(f"Failed to get all desktops via pyvda: {e}")
        return [get_current_desktop()]


def get_desktop_count() -> int:
    """Get the number of virtual desktops.

    Returns:
        Number of virtual desktops.
    """
    try:
        from pyvda import get_virtual_desktops

        return len(get_virtual_desktops())
    except Exception:
        return 1


def is_window_on_current_desktop(hwnd: int) -> bool:
    """Check if a window is on the current virtual desktop.

    Args:
        hwnd: Window handle.

    Returns:
        True if the window is on the current desktop.
    """
    try:
        from pyvda import AppView, VirtualDesktop

        app = AppView(hwnd)
        return app.desktop_id == VirtualDesktop.current().id
    except Exception as e:
        logger.warning(f"Failed to check window desktop: {e}")
        return True


def switch_desktop(index: int) -> bool:
    """Switch to a virtual desktop by index (0-based).

    Args:
        index: Zero-based index of the target desktop.

    Returns:
        True if successful.
    """
    try:
        from pyvda import get_virtual_desktops

        desktops = get_virtual_desktops()
        if 0 <= index < len(desktops):
            desktops[index].go()
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to switch desktop: {e}")
        return False


def move_window_to_desktop(hwnd: int, desktop_index: int) -> bool:
    """Move a window to a specific virtual desktop.

    Args:
        hwnd: Window handle.
        desktop_index: Zero-based index of the target desktop.

    Returns:
        True if successful.
    """
    try:
        from pyvda import AppView, get_virtual_desktops

        desktops = get_virtual_desktops()
        if 0 <= desktop_index < len(desktops):
            target_desktop = desktops[desktop_index]
            app = AppView(hwnd)
            app.move(target_desktop)
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to move window to desktop: {e}")
        return False
