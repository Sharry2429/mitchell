"""Tool schema and registry for managing and discovering executable tools."""

import importlib
import pkgutil
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Tool(BaseModel):
    """Tool schema representing an executable tool."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="Unique name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema representing tool parameters",
    )
    function: Callable[..., Any] = Field(
        ...,
        description="Callable implementation of the tool",
    )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Allow calling the tool instance directly."""
        return self.function(*args, **kwargs)


class ToolRegistry:
    """Registry for managing and discovering tools."""

    def __init__(self, auto_discover: bool = False) -> None:
        self._tools: Dict[str, Tool] = {}
        if auto_discover:
            self.discover()

    def register(self, tool: Tool) -> Tool:
        """Register a Tool instance."""
        if not isinstance(tool, Tool):
            raise TypeError(f"Expected Tool instance, got {type(tool).__name__}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[Tool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """Return a list of tool names and descriptions."""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    def get_all(self) -> Dict[str, Tool]:
        """Return a dictionary mapping tool names to Tool instances."""
        return dict(self._tools)

    def discover(self, package: str = "mitchell.tools") -> None:
        """Scan a tools package for modules exposing a TOOLS list and register them."""
        try:
            mod = importlib.import_module(package)
        except ImportError:
            return

        if not hasattr(mod, "__path__"):
            return

        for _, module_name, _ in pkgutil.iter_modules(mod.__path__, mod.__name__ + "."):
            if module_name.endswith(".registry"):
                continue
            try:
                submodule = importlib.import_module(module_name)
                tools_list = getattr(submodule, "TOOLS", None)
                if isinstance(tools_list, (list, tuple)):
                    for tool in tools_list:
                        if isinstance(tool, Tool):
                            self.register(tool)
            except Exception:
                pass


tool_registry = ToolRegistry(auto_discover=True)

__all__ = ["Tool", "ToolRegistry", "tool_registry"]
