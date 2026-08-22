"""Plugin manifest model and schema definition for Mitchell."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """Manifest describing a drop-in Mitchell plugin."""

    name: str = Field(..., description="Unique plugin identifier")
    version: str = Field(default="0.1.0", description="Semantic version string")
    description: str = Field(default="", description="Plugin description")
    author: Optional[str] = None
    entry_point: str = Field(default="plugin.py", description="Python file exposing TOOLS or register_plugin function")
    dependencies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
