"""Linked Knowledge Base engine supporting bidirectional wiki-links ([[Note]]), backlinks, tags, and graph search."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from mitchell.workspace.storage import workspace_storage


class KnowledgeNote(BaseModel):
    """A note entry within the linked knowledge base."""

    note_id: str
    title: str
    content: str = ""
    tags: List[str] = Field(default_factory=list)
    outgoing_links: List[str] = Field(default_factory=list)  # List of target note titles
    backlinks: List[str] = Field(default_factory=list)  # List of notes linking to this one
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotesEngine:
    """Operations engine for creating, linking, and querying the Mitchell linked knowledge graph."""

    def __init__(self) -> None:
        self.storage = workspace_storage

    def extract_links(self, content: str) -> List[str]:
        """Extract all [[Wiki Link]] targets from markdown content."""
        matches = re.findall(r"\[\[(.*?)\]\]", content)
        return [m.strip() for m in matches if m.strip()]

    def extract_tags(self, content: str) -> List[str]:
        """Extract all #hashtag references from markdown content."""
        matches = re.findall(r"(?:^|\s)#([a-zA-Z0-9_\-]+)", content)
        return list(set(matches))

    def create_note(self, title: str, content: str = "", tags: Optional[List[str]] = None) -> KnowledgeNote:
        """Create and save a new note."""
        note_id = re.sub(r"[^\w\-_\. ]", "_", title).strip().replace(" ", "_").lower()
        extracted_links = self.extract_links(content)
        all_tags = list(set((tags or []) + self.extract_tags(content)))

        note = KnowledgeNote(
            note_id=note_id,
            title=title,
            content=content or f"# {title}\n\n",
            tags=all_tags,
            outgoing_links=extracted_links,
        )

        self.save_note(note)
        return note

    def save_note(self, note: KnowledgeNote) -> None:
        """Persist note to workspace storage."""
        note.outgoing_links = self.extract_links(note.content)
        note.tags = list(set(note.tags + self.extract_tags(note.content)))
        note.updated_at = datetime.now(timezone.utc)

        rel_path = f"notes/{note.note_id}.md"
        self.storage.write_file(
            rel_path=rel_path,
            content=note.content,
            file_type="note",
            tags=note.tags,
            change_summary=f"Updated note {note.title}",
        )

    def load_note(self, note_id_or_title: str) -> Optional[KnowledgeNote]:
        """Load a note by ID or title and compute dynamic backlinks."""
        clean_id = re.sub(r"[^\w\-_\. ]", "_", note_id_or_title).strip().replace(" ", "_").lower().replace(".md", "")
        rel_path = f"notes/{clean_id}.md"
        try:
            content = self.storage.read_file(rel_path)
            title = clean_id.replace("_", " ").title()
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            note = KnowledgeNote(
                note_id=clean_id,
                title=title,
                content=content,
                tags=self.extract_tags(content),
                outgoing_links=self.extract_links(content),
            )
            # Find backlinks across other notes
            note.backlinks = self._find_backlinks_to(title)
            return note
        except Exception:
            return None

    def _find_backlinks_to(self, target_title: str) -> List[str]:
        """Scan all workspace notes to find which ones reference target_title."""
        all_notes = self.storage.list_files(sub_dir="notes")
        backlinks = []
        target_norm = target_title.strip().lower()

        for f in all_notes:
            if f["name"].endswith(".md"):
                try:
                    c = self.storage.read_file(f["path"])
                    links = [l.lower() for l in self.extract_links(c)]
                    if target_norm in links or target_norm.replace(" ", "_") in links:
                        backlinks.append(f["name"].replace(".md", "").replace("_", " ").title())
                except Exception:
                    continue
        return backlinks

    def list_notes(self) -> List[Dict[str, Any]]:
        """List all notes with tag and link metadata."""
        files = self.storage.list_files(sub_dir="notes")
        notes = []
        for f in files:
            note = self.load_note(f["name"])
            if note:
                notes.append({
                    "id": note.note_id,
                    "title": note.title,
                    "tags": note.tags,
                    "outgoing_links": note.outgoing_links,
                    "backlinks_count": len(note.backlinks),
                    "updated_at": f["updated_at"],
                })
        return notes

    def get_knowledge_graph(self) -> Dict[str, Any]:
        """Generate full node-link knowledge graph for 3D/2D visualization."""
        notes = self.list_notes()
        nodes = []
        links = []
        seen_nodes: Set[str] = set()

        for n in notes:
            node_id = n["title"]
            if node_id not in seen_nodes:
                nodes.append({"id": node_id, "group": "note", "tags": n["tags"]})
                seen_nodes.add(node_id)

            for target in n["outgoing_links"]:
                if target not in seen_nodes:
                    nodes.append({"id": target, "group": "uncreated", "tags": []})
                    seen_nodes.add(target)
                links.append({"source": node_id, "target": target})

        return {"nodes": nodes, "links": links}


notes_engine = NotesEngine()

__all__ = ["KnowledgeNote", "NotesEngine", "notes_engine"]
