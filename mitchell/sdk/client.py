"""Mitchell Python SDK — Fluent programmatic client library for autonomous agent workflows."""

from typing import Any, Dict, List, Optional

from mitchell.avatar.annotator import screen_annotator
from mitchell.avatar.state import AvatarStateEnum, avatar_manager
from mitchell.benchmark.runner import benchmark_runner
from mitchell.benchmark.scenarios import BENCHMARK_SUITE
from mitchell.daemon.queue import daemon_queue
from mitchell.daemon.scheduler import cron_scheduler
from mitchell.hive.teams import team_coordinator
from mitchell.manager import Manager
from mitchell.mcp_client.hub import mcp_hub
from mitchell.mesh.coordinator import mesh_coordinator
from mitchell.tools.registry import Tool, tool_registry
from mitchell.voice.stt import stt_engine
from mitchell.voice.tts import tts_engine


class VoiceNamespace:
    """Voice interaction namespace for Mitchell SDK."""

    def speak(self, text: str) -> None:
        """Speak text aloud using platform TTS."""
        tts_engine.speak(text)

    def listen(self) -> str:
        """Listen and transcribe microphone input."""
        return stt_engine.listen()


class ScreenNamespace:
    """Screen guidance and annotation namespace for Mitchell SDK."""

    def highlight(self, x: int, y: int, width: int = 120, height: int = 40, label: str = "") -> Any:
        """Highlight a visual region on the user's screen."""
        return screen_annotator.highlight_element(x=x, y=y, width=width, height=height, label=label)

    def point(self, from_x: int, from_y: int, to_x: int, to_y: int, label: str = "") -> Any:
        """Draw an instructional arrow on the screen."""
        return screen_annotator.point_arrow(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, label=label)

    def clear(self) -> None:
        """Clear all active on-screen annotations."""
        screen_annotator.clear()


class MeshNamespace:
    """Distributed mesh cluster namespace for Mitchell SDK."""

    def list_nodes(self) -> List[Dict[str, Any]]:
        """List active nodes in the mesh cluster."""
        return mesh_coordinator.list_nodes()

    def dispatch(self, goal: str, capability: Optional[str] = None) -> Any:
        """Dispatch a task to a remote mesh node."""
        from mitchell.mesh.protocol import MeshTaskRequest
        req = MeshTaskRequest(goal=goal, required_capability=capability)
        return mesh_coordinator.dispatch_task(req)


class QueueNamespace:
    """24/7 background queue namespace for Mitchell SDK."""

    def enqueue(self, goal: str, priority: int = 10) -> str:
        """Enqueue an autonomous task."""
        return daemon_queue.enqueue(goal=goal, priority=priority)

    def schedule(self, job_id: str, cron_expr: str, goal: str) -> Any:
        """Register a recurring cron task."""
        return cron_scheduler.add_job(job_id=job_id, cron_expr=cron_expr, goal=goal)


class MitchellClient:
    """The unified Mitchell SDK client."""

    def __init__(self, manager_instance: Optional[Manager] = None) -> None:
        self._manager = manager_instance or Manager()
        self.voice = VoiceNamespace()
        self.screen = ScreenNamespace()
        self.mesh = MeshNamespace()
        self.queue = QueueNamespace()
        self.teams = team_coordinator
        self.tools = tool_registry
        self.mcp = mcp_hub

    def do(self, goal: str) -> str:
        """Execute an autonomous goal through the multi-agent decision loop."""
        return self._manager.run(goal)

    def set_avatar_state(self, state_name: str, emotion: Optional[str] = None) -> Any:
        """Update 3D Avatar state."""
        enum_val = AvatarStateEnum(state_name.lower())
        return avatar_manager.set_state(enum_val, emotion=emotion)

    def run_benchmark(self, domain: Optional[str] = None) -> str:
        """Run the benchmarking evaluation arena."""
        scenarios = BENCHMARK_SUITE
        if domain:
            scenarios = [s for s in BENCHMARK_SUITE if s.domain == domain]
        scorecard = benchmark_runner.run_suite(scenarios=scenarios)
        return scorecard.generate_markdown_report()


def connect(manager_instance: Optional[Manager] = None) -> MitchellClient:
    """Create and return a connected Mitchell SDK client instance."""
    return MitchellClient(manager_instance=manager_instance)


__all__ = ["MitchellClient", "connect"]
