"""MeshNode representing a physical worker or leader instance in the Mitchell cluster."""

import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from mitchell.core.logging import logger
from mitchell.mesh.protocol import MeshCapability, MeshTaskRequest, MeshTaskResponse


class MeshNode:
    """A distributed node in the Mitchell agent mesh."""

    def __init__(
        self,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        is_leader: bool = False,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:6]}"
        self.node_name = node_name or f"Mitchell-{sys.platform.capitalize()}"
        self.is_leader = is_leader
        self.capabilities = capabilities or self._detect_default_capabilities()
        self.is_active = True

    def _detect_default_capabilities(self) -> List[str]:
        """Auto-detect default capabilities on the current machine."""
        caps = ["core", "browser"]
        if sys.platform == "win32":
            caps.append("windows_uia")
        if sys.platform.startswith("linux"):
            caps.append("linux_cli")
        if sys.platform == "darwin":
            caps.append("macos_say")
        return caps

    def get_capability_advertisement(self) -> MeshCapability:
        """Generate heartbeat capability advertisement."""
        return MeshCapability(
            node_id=self.node_id,
            node_name=self.node_name,
            platform=sys.platform,
            capabilities=self.capabilities,
            load_score=0.1,
            last_heartbeat=time.time(),
        )

    def execute_remote_task(self, request: MeshTaskRequest) -> MeshTaskResponse:
        """Execute a dispatched task locally and return response."""
        start_ts = time.time()
        logger.info("MeshNode [{}]: Executing task '{}' -> '{}'", self.node_id, request.task_id, request.goal)

        try:
            from mitchell.manager import Manager
            mgr = Manager()
            result = mgr.run(request.goal)
            duration = time.time() - start_ts
            return MeshTaskResponse(
                task_id=request.task_id,
                node_id=self.node_id,
                status="success",
                result=result,
                duration_s=duration,
            )
        except Exception as e:
            logger.error("MeshNode [{}]: Error executing task {}: {}", self.node_id, request.task_id, e)
            return MeshTaskResponse(
                task_id=request.task_id,
                node_id=self.node_id,
                status="failed",
                error=str(e),
                duration_s=time.time() - start_ts,
            )


__all__ = ["MeshNode"]
