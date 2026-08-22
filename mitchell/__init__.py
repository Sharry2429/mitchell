"""Mitchell — Autonomous Multi-Agent Hive & Task Orchestration Framework (v1.0.0)."""

__version__ = "1.0.0"

from mitchell.manager import Manager
from mitchell.sdk import MitchellClient, connect
from mitchell.tools.registry import tool_registry

__all__ = [
    "__version__",
    "Manager",
    "MitchellClient",
    "connect",
    "tool_registry",
]
