"""Mitchell Native Workspace Subsystem — Cross-Device Synced Files, Documents, Spreadsheets, Mail, Notes, Calendar, Projects."""

from mitchell.workspace.calendar import CalendarEngine, CalendarEvent, calendar_engine
from mitchell.workspace.documents import DocumentEngine, WorkspaceDocument, document_engine
from mitchell.workspace.mail import EmailMessage, MailEngine, mail_engine
from mitchell.workspace.manager import WorkspaceManager, workspace_manager
from mitchell.workspace.notes import KnowledgeNote, NotesEngine, notes_engine
from mitchell.workspace.projects import ProjectBoard, ProjectEngine, ProjectTask, project_engine
from mitchell.workspace.spreadsheet import Cell, Spreadsheet, SpreadsheetEngine, spreadsheet_engine
from mitchell.workspace.storage import FileVersion, WorkspaceFileMetadata, WorkspaceStorage, workspace_storage
from mitchell.workspace.sync import SyncBundle, SyncManifestEntry, WorkspaceSyncEngine, workspace_sync

__all__ = [
    "WorkspaceManager",
    "workspace_manager",
    "WorkspaceStorage",
    "workspace_storage",
    "DocumentEngine",
    "document_engine",
    "WorkspaceDocument",
    "SpreadsheetEngine",
    "spreadsheet_engine",
    "Spreadsheet",
    "Cell",
    "NotesEngine",
    "notes_engine",
    "KnowledgeNote",
    "ProjectEngine",
    "project_engine",
    "ProjectBoard",
    "ProjectTask",
    "MailEngine",
    "mail_engine",
    "EmailMessage",
    "CalendarEngine",
    "calendar_engine",
    "CalendarEvent",
    "WorkspaceSyncEngine",
    "workspace_sync",
    "SyncBundle",
    "SyncManifestEntry",
    "WorkspaceFileMetadata",
    "FileVersion",
]
