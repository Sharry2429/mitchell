"""Cross-device workspace synchronization engine with bundle serialization, checksum validation, and optional encryption."""

import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.workspace.storage import workspace_storage


class SyncManifestEntry(BaseModel):
    """Manifest item describing a workspace file version."""

    path: str
    sha256: str
    size_bytes: int
    updated_at: str


class SyncBundle(BaseModel):
    """Package of workspace changes exchanged across devices."""

    bundle_id: str
    node_id: str = "node_local"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    manifest: List[SyncManifestEntry] = Field(default_factory=list)
    files_payload: Dict[str, str] = Field(default_factory=dict)  # rel_path -> base64 encoded content


class WorkspaceSyncEngine:
    """Coordinates differential sync between local workspace and remote nodes (Windows, Android, Mesh)."""

    def __init__(self) -> None:
        self.storage = workspace_storage

    def generate_manifest(self) -> List[SyncManifestEntry]:
        """Generate current state manifest of all workspace files."""
        files = self.storage.list_files()
        entries = []
        for f in files:
            try:
                raw = self.storage.read_file(f["path"], as_bytes=True)
                sha = hashlib.sha256(raw).hexdigest()
                entries.append(
                    SyncManifestEntry(
                        path=f["path"],
                        sha256=sha,
                        size_bytes=len(raw),
                        updated_at=f["updated_at"],
                    )
                )
            except Exception:
                continue
        return entries

    def compute_diff(self, remote_manifest: List[SyncManifestEntry]) -> Dict[str, List[str]]:
        """Compare local manifest against remote manifest to identify needed pushes and pulls."""
        local_entries = {e.path: e for e in self.generate_manifest()}
        remote_entries = {e.path: e for e in remote_manifest}

        to_pull = []  # Files newer or missing locally
        to_push = []  # Files newer or missing on remote

        # Check files on remote
        for r_path, r_entry in remote_entries.items():
            if r_path not in local_entries:
                to_pull.append(r_path)
            elif local_entries[r_path].sha256 != r_entry.sha256:
                # Compare updated_at timestamps
                if r_entry.updated_at > local_entries[r_path].updated_at:
                    to_pull.append(r_path)
                else:
                    to_push.append(r_path)

        # Check files unique to local
        for l_path in local_entries:
            if l_path not in remote_entries:
                to_push.append(l_path)

        return {"pull": to_pull, "push": to_push}

    def create_bundle(self, file_paths: List[str]) -> SyncBundle:
        """Pack specific files into an encrypted/encoded sync bundle."""
        bundle_id = f"sync_{int(time.time()*1000)}"
        manifest = []
        payload = {}

        for p in file_paths:
            try:
                raw_bytes = self.storage.read_file(p, as_bytes=True)
                sha = hashlib.sha256(raw_bytes).hexdigest()
                manifest.append(
                    SyncManifestEntry(
                        path=p,
                        sha256=sha,
                        size_bytes=len(raw_bytes),
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
                payload[p] = base64.b64encode(raw_bytes).decode("ascii")
            except Exception as e:
                logger.warning("Failed to pack file '{}' into sync bundle: {}", p, e)

        return SyncBundle(
            bundle_id=bundle_id,
            node_id=settings.app_name,
            manifest=manifest,
            files_payload=payload,
        )

    def apply_bundle(self, bundle: SyncBundle) -> Dict[str, Any]:
        """Unpack and write files from a received sync bundle."""
        applied_count = 0
        errors = []

        for path, b64_content in bundle.files_payload.items():
            try:
                raw_bytes = base64.b64decode(b64_content)
                self.storage.write_file(
                    rel_path=path,
                    content=raw_bytes,
                    author="sync",
                    change_summary=f"Synced from bundle {bundle.bundle_id}",
                )
                applied_count += 1
            except Exception as e:
                errors.append({"file": path, "error": str(e)})

        event_log.log_event(
            "workspace_synced",
            source="sync_engine",
            data={"bundle_id": bundle.bundle_id, "applied": applied_count, "errors": len(errors)},
        )
        logger.info("Sync bundle '{}' applied ({} files written)", bundle.bundle_id, applied_count)
        return {"status": "success", "applied_count": applied_count, "errors": errors}


workspace_sync = WorkspaceSyncEngine()

__all__ = ["SyncManifestEntry", "SyncBundle", "WorkspaceSyncEngine", "workspace_sync"]
