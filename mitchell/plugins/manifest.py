"""Plugin manifest model and schema definition for Mitchell and Claude plugins."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class PluginManifest(BaseModel):
    """Manifest describing a drop-in Mitchell or Claude Code plugin."""

    name: str = Field(..., description="Unique plugin identifier")
    version: str = Field(default="0.1.0", description="Semantic version string")
    description: str = Field(default="", description="Plugin description")
    author: Optional[Union[str, Dict[str, Any]]] = None
    entry_point: Optional[str] = Field(default="plugin.py", description="Python file exposing TOOLS or register_plugin function")
    skills: Optional[Union[str, List[str], List[Dict[str, Any]]]] = Field(
        default=None, description="Path to skills folder or list of skill definitions"
    )
    agents: Optional[Union[str, List[Dict[str, Any]]]] = Field(
        default=None, description="Path to agents folder or list of agent definitions"
    )
    commands: Optional[Union[str, List[Dict[str, Any]]]] = Field(
        default=None, description="Path to commands or list of slash commands"
    )
    hooks: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Hooks configuration or path"
    )
    mcp_servers: Optional[Dict[str, Any]] = Field(
        default=None, description="MCP servers declared by this plugin"
    )
    dependencies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    marketplace: Optional[str] = Field(default=None, description="Marketplace source repository")
    enabled: bool = Field(default=True, description="Whether the plugin is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("author", mode="before")
    @classmethod
    def parse_author(cls, v: Any) -> Optional[Union[str, Dict[str, Any]]]:
        if isinstance(v, dict) and "name" in v:
            return v["name"]
        return v

