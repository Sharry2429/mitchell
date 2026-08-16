"""WinControl configuration — global safeguards toggle and runtime settings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

__all__ = ["WinControlConfig", "configure", "get_config"]

logger = logging.getLogger("wincontrol")


@dataclass
class WinControlConfig:
    """Global configuration for WinControl.

    Attributes:
        safeguards: When True, dangerous operations require confirmation and
            certain destructive actions are blocked. When False, ALL safety
            checks are disabled — the library operates with zero restrictions.
            Default is True.
        powershell_timeout: Default timeout in seconds for PowerShell commands.
        cmd_timeout: Default timeout in seconds for CMD commands.
        screenshot_backend: Preferred screenshot backend.
        log_level: Logging verbosity.
        shell_encoding: Encoding for shell output. None means auto-detect.
        max_shell_output: Maximum characters to capture from shell output.
            0 means unlimited.
        admin_elevation: Whether to attempt UAC elevation for admin operations.
    """

    safeguards: bool = True
    powershell_timeout: int = 30
    cmd_timeout: int = 30
    screenshot_backend: Literal["auto", "gdi", "dxcam"] = "auto"
    log_level: str = "WARNING"
    shell_encoding: str | None = None
    max_shell_output: int = 0
    admin_elevation: bool = True

    def __post_init__(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.WARNING)
        )
        logger.setLevel(getattr(logging, self.log_level.upper(), logging.WARNING))


# Global singleton
_config = WinControlConfig()


def get_config() -> WinControlConfig:
    """Return the current global configuration."""
    return _config


def configure(
    safeguards: bool | None = None,
    powershell_timeout: int | None = None,
    cmd_timeout: int | None = None,
    screenshot_backend: Literal["auto", "gdi", "dxcam"] | None = None,
    log_level: str | None = None,
    shell_encoding: str | None = None,
    max_shell_output: int | None = None,
    admin_elevation: bool | None = None,
) -> WinControlConfig:
    """Update global configuration. Only provided values are changed.

    Args:
        safeguards: Toggle safety checks on/off. False = unrestricted mode.
        powershell_timeout: Default PowerShell command timeout (seconds).
        cmd_timeout: Default CMD command timeout (seconds).
        screenshot_backend: Screenshot capture method ("auto", "gdi", "dxcam").
        log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR").
        shell_encoding: Shell output encoding. None = auto-detect.
        max_shell_output: Max shell output chars. 0 = unlimited.
        admin_elevation: Allow UAC elevation for admin operations.

    Returns:
        The updated configuration.
    """
    if safeguards is not None:
        _config.safeguards = safeguards
    if powershell_timeout is not None:
        _config.powershell_timeout = powershell_timeout
    if cmd_timeout is not None:
        _config.cmd_timeout = cmd_timeout
    if screenshot_backend is not None:
        _config.screenshot_backend = screenshot_backend
    if log_level is not None:
        _config.log_level = log_level
        logger.setLevel(getattr(logging, log_level.upper(), logging.WARNING))
    if shell_encoding is not None:
        _config.shell_encoding = shell_encoding
    if max_shell_output is not None:
        _config.max_shell_output = max_shell_output
    if admin_elevation is not None:
        _config.admin_elevation = admin_elevation

    return _config
