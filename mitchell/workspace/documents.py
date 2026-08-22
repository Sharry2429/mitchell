"""Rich document editor engine with structured outline, agent editing, and multi-format export."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.workspace.storage import workspace_storage


class DocumentSection(BaseModel):
    """A heading/section in a structured document."""

    heading: str
    level: int = 1
    content: str = ""
    subsections: List["DocumentSection"] = Field(default_factory=list)


class WorkspaceDocument(BaseModel):
    """Rich document model supporting Markdown, structured sections, and export."""

    doc_id: str
    title: str
    content: str = ""
    author: str = "agent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = Field(default_factory=list)

    def get_outline(self) -> List[Dict[str, Any]]:
        """Parse headings (# through ###) into a hierarchical table of contents."""
        outline = []
        for line in self.content.splitlines():
            match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                outline.append({"level": level, "title": title})
        return outline

    def append_section(self, heading: str, body: str, level: int = 2) -> None:
        """Append a structured section to the document."""
        prefix = "#" * level
        section_text = f"\n\n{prefix} {heading}\n\n{body.strip()}\n"
        self.content += section_text
        self.updated_at = datetime.now(timezone.utc)

    def to_html(self) -> str:
        """Generate formatted HTML representation of the document."""
        # Simple high-fidelity conversion
        body_html = self.content
        # Code blocks
        body_html = re.sub(
            r"```(\w*)\n([\s\S]*?)```",
            r'<pre><code class="language-\1">\2</code></pre>',
            body_html,
        )
        # Headings
        for i in range(6, 0, -1):
            body_html = re.sub(
                rf"^({'#' * i})\s+(.*)$",
                rf"<h{i}>\2</h{i}>",
                body_html,
                flags=re.MULTILINE,
            )
        # Bold and italics
        body_html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", body_html)
        body_html = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", body_html)
        # Paragraphs
        paragraphs = body_html.split("\n\n")
        formatted = []
        for p in paragraphs:
            p_strip = p.strip()
            if not p_strip.startswith("<h") and not p_strip.startswith("<pre") and p_strip:
                formatted.append(f"<p>{p_strip.replace(chr(10), '<br>')}</p>")
            else:
                formatted.append(p_strip)

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{self.title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #222; }}
    h1, h2, h3 {{ color: #111; margin-top: 1.5em; }}
    pre {{ background: #f4f4f5; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    code {{ font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.9em; }}
    p {{ margin: 1em 0; }}
  </style>
</head>
<body>
  <h1>{self.title}</h1>
  {''.join(formatted)}
</body>
</html>"""


class DocumentEngine:
    """Operations engine for creating, loading, and modifying native workspace documents."""

    def __init__(self) -> None:
        self.storage = workspace_storage

    def create_document(
        self,
        title: str,
        initial_content: str = "",
        tags: Optional[List[str]] = None,
        author: str = "agent",
    ) -> WorkspaceDocument:
        """Create a new document and persist to workspace."""
        filename = re.sub(r"[^\w\-_\. ]", "_", title).strip().replace(" ", "_").lower() + ".md"
        rel_path = f"documents/{filename}"
        doc_id = filename.replace(".md", "")

        doc = WorkspaceDocument(
            doc_id=doc_id,
            title=title,
            content=initial_content or f"# {title}\n\n*Created on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n",
            author=author,
            tags=tags or [],
        )

        self.save_document(doc, change_summary="Initial document creation")
        return doc

    def save_document(self, doc: WorkspaceDocument, change_summary: str = "") -> None:
        """Save document content to workspace storage."""
        rel_path = f"documents/{doc.doc_id}.md"
        self.storage.write_file(
            rel_path=rel_path,
            content=doc.content,
            file_type="document",
            author=doc.author,
            change_summary=change_summary,
            tags=doc.tags,
        )

    def load_document(self, doc_id: str) -> Optional[WorkspaceDocument]:
        """Load a document by ID."""
        clean_id = doc_id.replace(".md", "")
        rel_path = f"documents/{clean_id}.md"
        try:
            content = self.storage.read_file(rel_path)
            title = clean_id.replace("_", " ").title()
            # Try to read first heading as title
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            return WorkspaceDocument(doc_id=clean_id, title=title, content=content)
        except Exception:
            return None

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all workspace documents with outline summaries."""
        files = self.storage.list_files(sub_dir="documents")
        docs = []
        for f in files:
            doc = self.load_document(f["name"])
            if doc:
                docs.append({
                    "id": doc.doc_id,
                    "title": doc.title,
                    "path": f["path"],
                    "size_bytes": f["size_bytes"],
                    "updated_at": f["updated_at"],
                    "outline": doc.get_outline(),
                })
        return docs


document_engine = DocumentEngine()

__all__ = ["WorkspaceDocument", "DocumentSection", "DocumentEngine", "document_engine"]
