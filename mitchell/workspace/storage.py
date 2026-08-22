"""Local-first workspace storage engine with file versioning, metadata tracking, and rollback capabilities."""

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class FileVersion(BaseModel):
    """Metadata for a specific version of a workspace file."""

    version_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_path: str
    sha256: str
    size_bytes: int
    author: str = "agent"  # 'agent' | 'user' | 'sync'
    change_summary: str = ""


class WorkspaceFileMetadata(BaseModel):
    """Metadata and version history for a workspace file."""

    file_path: str  # Relative to workspace root
    title: str = ""
    file_type: str = "generic"  # 'document' | 'spreadsheet' | 'note' | 'code' | 'generic'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = Field(default_factory=list)
    pinned: bool = False
    versions: List[FileVersion] = Field(default_factory=list)


class WorkspaceStorage:
    """Manages the physical and versioned storage for the Mitchell native workspace."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root = Path(root_dir or settings.workspace_root)
        self.versions_dir = self.root / ".versions"
        self.meta_file = self.root / ".meta.json"
        self._metadata_cache: Dict[str, WorkspaceFileMetadata] = {}
        self._ensure_dirs()
        self._load_metadata()

    def _ensure_dirs(self) -> None:
        """Ensure workspace directory structure exists."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("documents", "spreadsheets", "notes", "projects", "mail", "calendar", "files"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def _load_metadata(self) -> None:
        """Load metadata index from disk."""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for path_str, meta_dict in data.items():
                        self._metadata_cache[path_str] = WorkspaceFileMetadata.model_validate(meta_dict)
            except Exception as e:
                logger.warning("Failed to load workspace metadata: {}", e)

    def _save_metadata(self) -> None:
        """Persist metadata index to disk."""
        try:
            with open(self.meta_file, "w", encoding="utf-8") as f:
                dumpable = {k: v.model_dump(mode="json") for k, v in self._metadata_cache.items()}
                json.dump(dumpable, f, indent=2)
        except Exception as e:
            logger.error("Failed to save workspace metadata: {}", e)

    def write_file(
        self,
        rel_path: str,
        content: str | bytes,
        file_type: str = "generic",
        author: str = "agent",
        change_summary: str = "",
        tags: Optional[List[str]] = None,
    ) -> WorkspaceFileMetadata:
        """Write a file into the workspace with automatic version snapshotting."""
        rel_path = rel_path.replace("\\", "/").lstrip("/")
        full_path = self.root / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        is_bytes = isinstance(content, bytes)
        raw_bytes = content if is_bytes else content.encode("utf-8")
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Write current state
        if is_bytes:
            with open(full_path, "wb") as f:
                f.write(raw_bytes)
        else:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Create version snapshot if versioning enabled
        version_id = f"v_{int(time.time()*1000)}"
        if settings.workspace_versioning:
            ver_file = self.versions_dir / f"{sha256}_{version_id}"
            with open(ver_file, "wb") as vf:
                vf.write(raw_bytes)

        # Update metadata
        meta = self._metadata_cache.get(rel_path)
        if not meta:
            meta = WorkspaceFileMetadata(
                file_path=rel_path,
                title=Path(rel_path).stem.replace("_", " ").title(),
                file_type=file_type,
                tags=tags or [],
            )
            self._metadata_cache[rel_path] = meta

        ver_obj = FileVersion(
            version_id=version_id,
            file_path=rel_path,
            sha256=sha256,
            size_bytes=len(raw_bytes),
            author=author,
            change_summary=change_summary,
        )
        meta.versions.append(ver_obj)
        if len(meta.versions) > settings.workspace_max_versions:
            meta.versions = meta.versions[-settings.workspace_max_versions:]

        meta.updated_at = datetime.now(timezone.utc)
        if tags:
            meta.tags = list(set(meta.tags + tags))
        self._save_metadata()

        event_log.log_event(
            "workspace_file_written",
            source="workspace_storage",
            data={"file": rel_path, "type": file_type, "size": len(raw_bytes), "author": author},
        )
        logger.info("Workspace file '{}' written ({} bytes, version {})", rel_path, len(raw_bytes), version_id)
        return meta

    def read_file(self, rel_path: str, as_bytes: bool = False) -> str | bytes:
        """Read a workspace file."""
        rel_path = rel_path.replace("\\", "/").lstrip("/")
        full_path = self.root / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Workspace file not found: {rel_path}")

        if as_bytes:
            with open(full_path, "rb") as f:
                return f.read()
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def list_files(self, sub_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files in workspace with metadata and size."""
        target_dir = self.root / sub_dir if sub_dir else self.root
        results = []

        if not target_dir.exists():
            return results

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.startswith("."):
                    continue
                full = Path(root) / file
                rel = full.relative_to(self.root).as_posix()
                meta = self._metadata_cache.get(rel)
                stat = full.stat()

                results.append({
                    "path": rel,
                    "name": file,
                    "size_bytes": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "file_type": meta.file_type if meta else "generic",
                    "title": meta.title if meta else file,
                    "tags": meta.tags if meta else [],
                    "version_count": len(meta.versions) if meta else 1,
                })

        return sorted(results, key=lambda x: x["updated_at"], reverse=True)

    def rollback(self, rel_path: str, version_id: str) -> bool:
        """Rollback a file to a previous version snapshot."""
        rel_path = rel_path.replace("\\", "/").lstrip("/")
        meta = self._metadata_cache.get(rel_path)
        if not meta:
            return False

        target_ver = next((v for v in meta.versions if v.version_id == version_id), None)
        if not target_ver:
            return False

        ver_file = self.versions_dir / f"{target_ver.sha256}_{target_ver.version_id}"
        if not ver_file.exists():
            return False

        full_path = self.root / rel_path
        shutil.copy2(ver_file, full_path)
        meta.updated_at = datetime.now(timezone.utc)
        meta.versions.append(
            FileVersion(
                version_id=f"v_rollback_{int(time.time()*1000)}",
                file_path=rel_path,
                sha256=target_ver.sha256,
                size_bytes=target_ver.size_bytes,
                author="rollback",
                change_summary=f"Rolled back to {version_id}",
            )
        )
        self._save_metadata()
        logger.info("Workspace file '{}' rolled back to version {}", rel_path, version_id)
        return True

    def delete_file(self, rel_path: str) -> bool:
        """Delete a workspace file."""
        rel_path = rel_path.replace("\\", "/").lstrip("/")
        full_path = self.root / rel_path
        if full_path.exists():
            full_path.unlink()
            self._metadata_cache.pop(rel_path, None)
            self._save_metadata()
            return True
        return False


workspace_storage = WorkspaceStorage()

__all__ = ["WorkspaceStorage", "workspace_storage", "WorkspaceFileMetadata", "FileVersion"]
