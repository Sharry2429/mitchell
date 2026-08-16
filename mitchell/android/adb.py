"""
mitchell.android.adb
Single shared ADB client.  Every Android module MUST use this instead of
calling subprocess directly.
"""

import subprocess

from mitchell.android.connection import get_adb_prefix
from mitchell.core.errors import (
    DeviceOffline,
    SystemMCPError,
)
from mitchell.core.errors import (
    TimeoutError as MCPTimeout,
)

# Default timeout for ADB commands (seconds)
_DEFAULT_TIMEOUT = 30


def shell(command, *, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Run a shell command *on the Android device* and return stdout.

    Equivalent to ``adb -s <serial> shell <command>``.

    Raises:
        DeviceOffline  – device is not reachable.
        MCPTimeout     – command exceeded *timeout* seconds.
        SystemMCPError – non-zero exit code or unexpected failure.
    """
    try:
        prefix = get_adb_prefix()
    except DeviceOffline:
        raise

    if isinstance(command, str):
        cmd_args = prefix + ["shell", command]
    else:
        cmd_args = prefix + ["shell"] + list(command)

    try:
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise DeviceOffline("adb binary not found on PATH.")
    except subprocess.TimeoutExpired:
        raise MCPTimeout(f"ADB shell command timed out after {timeout}s: {command}")

    if result.returncode != 0 and result.stderr.strip():
        raise SystemMCPError(f"ADB shell error: {result.stderr.strip()}")

    return result.stdout.strip()


def run(args: list[str], *, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Run an arbitrary ADB sub-command (e.g. ``["push", src, dst]``).

    Raises:
        DeviceOffline  – device is not reachable.
        MCPTimeout     – command exceeded *timeout* seconds.
        SystemMCPError – non-zero exit code or unexpected failure.
    """
    try:
        prefix = get_adb_prefix()
    except DeviceOffline:
        raise

    try:
        result = subprocess.run(
            prefix + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise DeviceOffline("adb binary not found on PATH.")
    except subprocess.TimeoutExpired:
        raise MCPTimeout(f"ADB command timed out after {timeout}s: {' '.join(args)}")

    if result.returncode != 0 and result.stderr.strip():
        raise SystemMCPError(f"ADB error: {result.stderr.strip()}")

    return result.stdout.strip()


def run_background(command: str) -> None:
    """Fire-and-forget a shell command on the device (``nohup … &``).

    Raises:
        DeviceOffline – device is not reachable.
    """
    try:
        prefix = get_adb_prefix()
    except DeviceOffline:
        raise

    try:
        subprocess.Popen(
            prefix + ["shell", f"nohup {command} &"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise DeviceOffline("adb binary not found on PATH.")
