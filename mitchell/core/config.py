"""
mitchell.core.config
Central configuration for System-MCP.
"""

import os
from dataclasses import dataclass


@dataclass
class SystemMCPConfig:
    safeguards: bool = True
    unattended_mode: bool = False
    action_timeout: float = 10.0
    retry_attempts: int = 2
    retry_delay: float = 0.5
    screenshot_dir: str = "/tmp/system-mcp/screenshots"
    # Android specific
    reconnect_on_failure: bool = True
    use_scrcpy: bool = False

    @classmethod
    def from_env(cls) -> "SystemMCPConfig":
        def _get_bool(name: str, default: bool) -> bool:
            val = os.environ.get(name)
            if val is not None:
                return val.lower() not in ("0", "false", "no")
            return default

        def _get_float(name: str, default: float) -> float:
            val = os.environ.get(name)
            return float(val) if val is not None else default

        def _get_int(name: str, default: int) -> int:
            val = os.environ.get(name)
            return int(val) if val is not None else default

        return cls(
            safeguards=_get_bool("SYSTEM_MCP_SAFEGUARDS", True),
            unattended_mode=_get_bool("SYSTEM_MCP_UNATTENDED", False),
            action_timeout=_get_float("SYSTEM_MCP_ACTION_TIMEOUT", 10.0),
            retry_attempts=_get_int("SYSTEM_MCP_RETRY_ATTEMPTS", 2),
            retry_delay=_get_float("SYSTEM_MCP_RETRY_DELAY", 0.5),
            screenshot_dir=os.environ.get(
                "SYSTEM_MCP_SCREENSHOT_DIR", "/tmp/system-mcp/screenshots"
            ),
            reconnect_on_failure=_get_bool("SYSTEM_MCP_RECONNECT", True),
            use_scrcpy=_get_bool("SYSTEM_MCP_USE_SCRCPY", False),
        )


_global_config = SystemMCPConfig.from_env()


def get_config() -> SystemMCPConfig:
    return _global_config


def configure(**kwargs):
    for k, v in kwargs.items():
        if hasattr(_global_config, k):
            setattr(_global_config, k, v)
