"""
mitchell.core.tool_registry
Auto-discovers and registers tools from windows/, android/, and browser/ pillars.
"""
import importlib
import inspect
import os

from fastmcp import FastMCP

# Initialize MCP Server instance
mcp = FastMCP("System-MCP")

def _register_pillar(platform: str):
    """Auto-discovers and registers all tools in a given pillar."""
    # Find the directory of the pillar relative to the package root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(current_dir)
    pillar_dir = os.path.join(package_dir, platform)
    
    if not os.path.isdir(pillar_dir):
        return
        
    for filename in os.listdir(pillar_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            mod_name = filename[:-3]
            try:
                mod = importlib.import_module(f"mitchell.{platform}.{mod_name}")
                for name, func in inspect.getmembers(mod, inspect.isfunction):
                    if name.startswith("_"):
                        continue
                    
                    if getattr(func, "__module__", "") != mod.__name__:
                        continue
                        
                    if getattr(func, "_mcp_exclude", False):
                        continue
                    
                    if platform == "browser":
                        # Browser module keeps natural browser_* names
                        tool_name = name if name.startswith("browser_") else f"browser_{name}"
                    else:
                        tool_name = f"{platform}_{mod_name}_{name}"
                    
                    func.__name__ = tool_name
                    try:
                        mcp.add_tool(func)
                    except Exception as e:
                        print(f"Skipping tool {tool_name}: {e}")
                        
            except ImportError as e:
                print(f"ImportError loading {platform}.{mod_name}: {e}")

def _register_all():
    _register_pillar("windows")
    _register_pillar("android")
    _register_pillar("browser")

_register_all()
