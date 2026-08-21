"""Mitchell Hive package for multi-agent coordination."""

from mitchell.hive.agents.base import BaseAgent
from mitchell.hive.agents.echo import EchoAgent
from mitchell.hive.router import HiveRouter, hive_router

__all__ = ["BaseAgent", "EchoAgent", "HiveRouter", "hive_router"]
