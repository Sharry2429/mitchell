"""Workspace Worker Agent executing document, spreadsheet, note, and project tasks."""

import json
from typing import Any, Dict, Union

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.workspace import (
    calendar_engine,
    document_engine,
    mail_engine,
    notes_engine,
    project_engine,
    spreadsheet_engine,
    workspace_manager,
)


class WorkspaceWorkerAgent(BaseAgent):
    """Hive Agent specializing in native workspace operations (documents, sheets, notes, projects)."""

    def __init__(
        self,
        agent_id: str = "workspace_worker",
        description: str = "Manages files, documents, spreadsheets, notes, calendar, and project boards in Native Workspace",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process workspace action."""
        logger.info("WorkspaceWorker received task from {}: {}", sender, message)

        if isinstance(message, dict):
            action = message.get("action", "")
            data = message
        else:
            text = str(message).strip()
            parts = text.split(maxsplit=1)
            action = parts[0].lower() if parts else ""
            data = {"raw": parts[1]} if len(parts) > 1 else {}

        event_log.log_event(
            "workspace_worker_task_started",
            source=self.agent_id,
            data={"action": action, "sender": sender},
        )

        try:
            if action in ("create_doc", "document"):
                title = data.get("title") or data.get("raw") or "Untitled Document"
                content = data.get("content", "")
                doc = document_engine.create_document(title=title, initial_content=content)
                return {"status": "success", "doc_id": doc.doc_id, "title": doc.title}

            elif action in ("create_sheet", "sheet"):
                title = data.get("title") or data.get("raw") or "Sheet"
                sheet = spreadsheet_engine.create_sheet(title=title)
                return {"status": "success", "sheet_id": sheet.sheet_id, "title": sheet.title}

            elif action in ("create_note", "note"):
                title = data.get("title") or data.get("raw") or "Note"
                content = data.get("content", "")
                note = notes_engine.create_note(title=title, content=content)
                return {"status": "success", "note_id": note.note_id, "title": note.title}

            elif action in ("create_project", "project", "kanban"):
                title = data.get("title") or data.get("raw") or "Project"
                board = project_engine.create_board(title=title)
                return {"status": "success", "board_id": board.board_id, "title": board.title}

            elif action in ("summary", "status"):
                return {"status": "success", "summary": workspace_manager.get_summary()}

            elif action in ("search", "find"):
                query = data.get("query") or data.get("raw") or ""
                results = workspace_manager.search_workspace(query)
                return {"status": "success", "results": results}

            return {"status": "success", "message": f"Workspace task processed: {message}"}

        except Exception as e:
            logger.error("WorkspaceWorker error: {}", e)
            return {"status": "error", "error": str(e)}


__all__ = ["WorkspaceWorkerAgent"]
