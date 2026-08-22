"""Project management and Kanban board engine for autonomous agent task tracking and user projects."""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from mitchell.workspace.storage import workspace_storage


class ProjectTask(BaseModel):
    """A task card within a project board."""

    id: str = Field(default_factory=lambda: f"task_{str(uuid.uuid4())[:8]}")
    title: str
    description: str = ""
    status: Literal["backlog", "todo", "in_progress", "review", "done"] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    assignee: str = "agent"  # 'agent' | 'user' | agent_name
    due_date: Optional[str] = None
    checklist: List[Dict[str, Any]] = Field(default_factory=list)  # [{"item": "text", "done": bool}]
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectBoard(BaseModel):
    """A project Kanban board containing grouped task cards."""

    board_id: str
    title: str
    description: str = ""
    tasks: List[ProjectTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_task(
        self,
        title: str,
        description: str = "",
        status: Literal["backlog", "todo", "in_progress", "review", "done"] = "todo",
        priority: Literal["low", "medium", "high", "urgent"] = "medium",
        assignee: str = "agent",
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ProjectTask:
        """Add a new task card."""
        task = ProjectTask(
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee=assignee,
            due_date=due_date,
            tags=tags or [],
        )
        self.tasks.append(task)
        self.updated_at = datetime.now(timezone.utc)
        return task

    def update_task_status(self, task_id: str, new_status: Literal["backlog", "todo", "in_progress", "review", "done"]) -> bool:
        """Move a task to a different status column."""
        for t in self.tasks:
            if t.id == task_id:
                t.status = new_status
                t.updated_at = datetime.now(timezone.utc)
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def get_column_view(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get tasks grouped by Kanban status columns."""
        cols: Dict[str, List[Dict[str, Any]]] = {
            "backlog": [],
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": [],
        }
        for t in self.tasks:
            if t.status in cols:
                cols[t.status].append(t.model_dump(mode="json"))
        return cols

    def get_progress(self) -> Dict[str, Any]:
        """Calculate board completion metrics."""
        total = len(self.tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "percent": 100.0}
        done = sum(1 for t in self.tasks if t.status == "done")
        return {
            "total": total,
            "completed": done,
            "in_progress": sum(1 for t in self.tasks if t.status == "in_progress"),
            "percent": round((done / total) * 100, 1),
        }


class ProjectEngine:
    """Operations engine for creating, loading, and managing project Kanban boards."""

    def __init__(self) -> None:
        self.storage = workspace_storage

    def create_board(self, title: str, description: str = "") -> ProjectBoard:
        """Create a new project board."""
        board_id = re.sub(r"[^\w\-_\. ]", "_", title).strip().replace(" ", "_").lower()
        board = ProjectBoard(board_id=board_id, title=title, description=description)
        self.save_board(board, change_summary="Board creation")
        return board

    def save_board(self, board: ProjectBoard, change_summary: str = "") -> None:
        """Persist board state to workspace storage."""
        rel_path = f"projects/{board.board_id}.json"
        self.storage.write_file(
            rel_path=rel_path,
            content=board.model_dump_json(indent=2),
            file_type="project",
            change_summary=change_summary,
        )

    def load_board(self, board_id: str) -> Optional[ProjectBoard]:
        """Load a project board by ID."""
        clean_id = board_id.replace(".json", "")
        rel_path = f"projects/{clean_id}.json"
        try:
            content = self.storage.read_file(rel_path)
            data = json.loads(content)
            return ProjectBoard.model_validate(data)
        except Exception:
            return None

    get_board = load_board

    def list_boards(self) -> List[Dict[str, Any]]:
        """List all project boards with progress overview."""
        files = self.storage.list_files(sub_dir="projects")
        boards = []
        for f in files:
            board = self.load_board(f["name"])
            if board:
                boards.append({
                    "id": board.board_id,
                    "title": board.title,
                    "description": board.description,
                    "progress": board.get_progress(),
                    "updated_at": f["updated_at"],
                })
        return boards


project_engine = ProjectEngine()

__all__ = ["ProjectTask", "ProjectBoard", "ProjectEngine", "project_engine"]
