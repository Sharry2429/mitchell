"""Mitchell manager package for coordination and execution loops."""

from mitchell.manager.intent import Intent, parse_fast_intent, parse_tool_args
from mitchell.manager.loop import Manager, ManagerLoop, Message

__all__ = [
    "Intent",
    "parse_fast_intent",
    "parse_tool_args",
    "Manager",
    "ManagerLoop",
    "Message",
]
