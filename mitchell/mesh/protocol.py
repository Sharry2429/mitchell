"""Wire protocol and message models for Mitchell's distributed agent mesh."""

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MeshCapability(BaseModel):
    """Capabilities advertised by a physical mesh node."""

    node_id: str
    node_name: str
    platform: str
    capabilities: List[str] = Field(default_factory=list)  # e.g., ["browser", "windows_uia", "android_adb", "gpu", "local_llm"]
    load_score: float = 0.0  # 0.0 (idle) to 1.0 (busy)
    last_heartbeat: float = Field(default_factory=time.time)


class MeshTaskRequest(BaseModel):
    """Task dispatched across the mesh to a remote node."""

    task_id: str = Field(default_factory=lambda: f"mesh_{uuid.uuid4().hex[:8]}")
    target_node_id: Optional[str] = None
    required_capability: Optional[str] = None
    goal: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timeout_s: float = 60.0


class MeshTaskResponse(BaseModel):
    """Result returned by a remote mesh node."""

    task_id: str
    node_id: str
    status: str  # "success", "failed", "timeout"
    result: Any = None
    error: Optional[str] = None
    duration_s: float = 0.0
