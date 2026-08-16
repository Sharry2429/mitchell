"""
Tool Registry with auto-discovery for all pillars (Windows, Android, Browser).
"""

import importlib
import inspect
import pkgutil
from typing import Callable, Any

from mcp.server.fastmcp import FastMCP

# Global FastMCP instance
mcp = FastMCP("Mitchell")

# Fallback for internal use (if needed)
_registry: dict[str, Callable] = {}

def get_registry() -> dict[str, Callable]:
    """Returns the populated tool registry (dict form for legacy/internal)."""
    if not _registry:
        discover_all_tools()
    return _registry

def _register_module_tools(platform: str, mod_name: str):
    """Registers all valid functions in a given module."""
    try:
        mod = importlib.import_module(f"mitchell.{platform}.{mod_name}")
        for name, func in inspect.getmembers(mod, inspect.isfunction):
            # Skip private functions
            if name.startswith("_"):
                continue
                
            # Only register functions defined in this module
            if func.__module__ != mod.__name__:
                continue
                
            # Respect explicit exclusion
            if getattr(func, "_mcp_exclude", False):
                continue
                
            # Prefix the tool name with the platform and module for a unified namespace
            tool_name = f"{platform}_{mod_name}_{name}"
            
            # For browser, we keep natural names as they are already prefixed
            if platform == "browser" and name.startswith("browser_"):
                tool_name = name
                
            _registry[tool_name] = func
            mcp.add_tool(func, name=tool_name)
    except ImportError as e:
        print(f"ImportError loading {platform}.{mod_name}: {e}")

def discover_all_tools():
    """Auto-discovers and registers tools from windows, android, and browser pillars."""
    pillars = ["windows", "android", "browser"]
    
    for platform in pillars:
        try:
            # Import the platform package to discover submodules
            platform_pkg = importlib.import_module(f"mitchell.{platform}")
            # Ensure the platform package has a __path__ attribute
            if hasattr(platform_pkg, "__path__"):
                for _, mod_name, _ in pkgutil.iter_modules(platform_pkg.__path__):
                    _register_module_tools(platform, mod_name)
        except ImportError as e:
            print(f"Failed to import pillar {platform}: {e}")
