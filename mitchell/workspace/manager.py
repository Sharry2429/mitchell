"""Central Workspace Manager unifying Documents, Spreadsheets, Notes, Projects, Mail, Calendar, and Sync."""

from typing import Any, Dict, List, Optional

from mitchell.workspace.calendar import calendar_engine, CalendarEvent
from mitchell.workspace.documents import document_engine, WorkspaceDocument
from mitchell.workspace.mail import mail_engine, EmailMessage
from mitchell.workspace.notes import notes_engine, KnowledgeNote
from mitchell.workspace.projects import project_engine, ProjectBoard
from mitchell.workspace.spreadsheet import spreadsheet_engine, Spreadsheet
from mitchell.workspace.storage import workspace_storage, WorkspaceStorage
from mitchell.workspace.sync import workspace_sync, WorkspaceSyncEngine


class WorkspaceManager:
    """Unified entry point providing deep agent access and Studio endpoints to all native workspace capabilities."""

    def __init__(self) -> None:
        self.storage = workspace_storage
        self.documents = document_engine
        self.spreadsheets = spreadsheet_engine
        self.notes = notes_engine
        self.projects = project_engine
        self.mail = mail_engine
        self.calendar = calendar_engine
        self.sync = workspace_sync

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate high-level overview of the entire workspace."""
        return {
            "total_files": len(self.storage.list_files()),
            "documents": len(self.documents.list_documents()),
            "spreadsheets": len(self.storage.list_files(sub_dir="spreadsheets")),
            "notes": len(self.notes.list_notes()),
            "project_boards": len(self.projects.list_boards()),
            "unread_mail": len(self.mail.list_emails(folder="inbox")),
            "upcoming_events": len(self.calendar.list_upcoming_events(days=7)),
        }

    def search_workspace(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Unified full-text search across all workspace components."""
        q = query.lower()
        results: Dict[str, List[Dict[str, Any]]] = {
            "documents": [],
            "spreadsheets": [],
            "notes": [],
            "projects": [],
            "mail": [],
        }

        # Search documents
        for doc_info in self.documents.list_documents():
            doc = self.documents.load_document(doc_info["id"])
            if doc and (q in doc.title.lower() or q in doc.content.lower()):
                results["documents"].append({"id": doc.doc_id, "title": doc.title, "type": "document"})

        # Search notes
        for note_info in self.notes.list_notes():
            note = self.notes.load_note(note_info["id"])
            if note and (q in note.title.lower() or q in note.content.lower()):
                results["notes"].append({"id": note.note_id, "title": note.title, "type": "note"})

        # Search projects
        for b_info in self.projects.list_boards():
            board = self.projects.load_board(b_info["id"])
            if board:
                matched_tasks = [t.title for t in board.tasks if q in t.title.lower() or q in t.description.lower()]
                if q in board.title.lower() or matched_tasks:
                    results["projects"].append({"id": board.board_id, "title": board.title, "matched_tasks": matched_tasks})

        # Search mail
        mail_matches = self.mail.list_emails(search_query=query)
        results["mail"] = [{"id": m["id"], "subject": m["subject"], "sender": m["sender"]} for m in mail_matches[:5]]

        return results


workspace_manager = WorkspaceManager()

__all__ = ["WorkspaceManager", "workspace_manager"]
