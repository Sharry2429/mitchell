import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class TaskState:
    PENDING = "pending"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskStep:
    description: str
    state: str = TaskState.PENDING
    action: str | None = None
    args: dict[str, Any] | None = None
    verification_passed: bool = False
    retries: int = 0
    error: str | None = None
    depends_on: list[int] = field(default_factory=list)
    claimed_by: str | None = None
    claimed_at: float | None = None
    
@dataclass
class Task:
    id: str
    instruction: str
    steps: list[TaskStep] = field(default_factory=list)
    state: str = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def get_log_path(self) -> Path:
        p = Path(os.path.expanduser(f"~/.system-mcp/tasks/{self.id}.json"))
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
        
    def save(self):
        with open(self.get_log_path(), "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, task_id: str) -> Optional["Task"]:
        p = Path(os.path.expanduser(f"~/.system-mcp/tasks/{task_id}.json"))
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            steps = [TaskStep(**s) for s in data.pop("steps", [])]
            return cls(**data, steps=steps)

def list_tasks(state: str | None = None) -> list["Task"]:
    """Discover persisted tasks from the task queue directory.

    Args:
        state: if set, only return tasks whose `state` matches. Otherwise all.

    Returns tasks ordered by creation time (oldest first).
    """
    tasks_dir = Path(os.path.expanduser("~/.system-mcp/tasks"))
    if not tasks_dir.exists():
        return []

    result: list[Task] = []
    for p in tasks_dir.glob("*.json"):
        if p.name.endswith(".lock_dir"):
            continue
        t = Task.load(p.stem)
        if t is None:
            continue
        if state is None or t.state == state:
            result.append(t)

    result.sort(key=lambda t: t.created_at)
    return result


list_tasks._mcp_exclude = True  # see mcp_server.register_platform_tools


def list_tasks_as_dicts(state: str | None = None) -> list[dict]:
    """MCP-safe wrapper — returns plain dicts so FastMCP's schema builder
    never has to resolve the Task dataclass by name."""
    return [asdict(t) for t in list_tasks(state)]


def task_all_terminal(task: "Task") -> bool:
    """True when every step is in a terminal state (nothing pending/running)."""
    return bool(task.steps) and all(
        s.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.SKIPPED)
        for s in task.steps
    )


def log_task_step(task_id: str, description: str, state: str = TaskState.COMPLETED) -> str:
    """Log a step for a given task ID."""
    task = Task.load(task_id)
    if not task:
        return f"Task {task_id} not found."
    
    step = TaskStep(description=description, state=state)
    task.steps.append(step)
    task.save()
    return f"Successfully logged step: {description} (State: {state})"
