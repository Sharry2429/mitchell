"""Workspace tools for the Mitchell ToolRegistry exposing documents, spreadsheets, notes, projects, and storage."""

import json
from typing import Any, Dict, List, Optional

from mitchell.tools.registry import Tool
from mitchell.workspace import (
    calendar_engine,
    document_engine,
    mail_engine,
    notes_engine,
    project_engine,
    spreadsheet_engine,
    workspace_manager,
    workspace_storage,
)


def tool_workspace_summary() -> str:
    """Get high-level summary of files, documents, sheets, notes, and boards in Mitchell Workspace."""
    summary = workspace_manager.get_summary()
    return json.dumps(summary, indent=2)


def tool_workspace_document_create(title: str, content: str = "") -> str:
    """Create a new rich document in the workspace."""
    doc = document_engine.create_document(title=title, initial_content=content)
    return f"Created document '{doc.title}' (ID: {doc.doc_id})"


def tool_workspace_document_read(doc_id: str) -> str:
    """Read a document from the workspace by ID."""
    doc = document_engine.load_document(doc_id)
    if not doc:
        return f"Document '{doc_id}' not found."
    return doc.content


def tool_workspace_spreadsheet_create(title: str) -> str:
    """Create a new spreadsheet in the workspace."""
    sheet = spreadsheet_engine.create_sheet(title)
    return f"Created spreadsheet '{sheet.title}' (ID: {sheet.sheet_id})"


def tool_workspace_note_create(title: str, content: str = "", tags: Optional[str] = None) -> str:
    """Create a linked knowledge note."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    note = notes_engine.create_note(title=title, content=content, tags=tag_list)
    return f"Created note '{note.title}' with {len(note.outgoing_links)} links and {len(note.tags)} tags."


def tool_workspace_search(query: str) -> str:
    """Unified search across all workspace documents, notes, spreadsheets, and tasks."""
    results = workspace_manager.search_workspace(query)
    return json.dumps(results, indent=2)


# Tool definitions
workspace_summary_tool = Tool(
    name="workspace_get_summary",
    description="Retrieve statistical summary of files, documents, spreadsheets, notes, and projects in the native workspace.",
    parameters={"type": "object", "properties": {}},
    function=tool_workspace_summary,
)

doc_create_tool = Tool(
    name="workspace_document_create",
    description="Create a new formatted markdown document in the native workspace.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title"},
            "content": {"type": "string", "description": "Markdown body content"},
        },
        "required": ["title"],
    },
    function=tool_workspace_document_create,
)

doc_read_tool = Tool(
    name="workspace_document_read",
    description="Read the markdown contents of a workspace document by its ID.",
    parameters={
        "type": "object",
        "properties": {
            "doc_id": {"type": "string", "description": "Document ID or filename"},
        },
        "required": ["doc_id"],
    },
    function=tool_workspace_document_read,
)

note_create_tool = Tool(
    name="workspace_note_create",
    description="Create a linked knowledge note with [[Wiki Links]] and tags.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Note title"},
            "content": {"type": "string", "description": "Note content with [[WikiLinks]]"},
            "tags": {"type": "string", "description": "Comma-separated tags"},
        },
        "required": ["title"],
    },
    function=tool_workspace_note_create,
)

workspace_search_tool = Tool(
    name="workspace_search",
    description="Unified full-text search across documents, notes, spreadsheets, and tasks in Mitchell Workspace.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword or phrase"},
        },
        "required": ["query"],
    },
    function=tool_workspace_search,
)

TOOLS = [
    workspace_summary_tool,
    doc_create_tool,
    doc_read_tool,
    note_create_tool,
    workspace_search_tool,
]
