"""Same-network direct file and folder transfer engine between Windows, Android, and Mesh nodes."""

import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class TransferJob(BaseModel):
    """Metadata tracking an active or completed cross-device file transfer."""

    job_id: str
    file_name: str
    file_size_bytes: int
    source_device: str
    target_device: str
    status: str = "completed"  # 'pending' | 'in_progress' | 'completed' | 'failed'
    sha256: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FileTransferEngine:
    """Handles direct file pushing, pulling, and ADB transfer to mobile/mesh devices."""

    def transfer_to_android(self, local_path: str, remote_android_path: str = "/sdcard/Download/") -> TransferJob:
        """Push a file from PC to Android via ADB."""
        import time
        from mitchell.android.engine import android_engine

        local = Path(local_path).resolve()
        if not local.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        file_size = local.stat().st_size
        raw = local.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()

        job_id = f"xfer_{int(time.time()*1000)}"

        # Execute ADB push
        res = android_engine.adb.run_adb_command(f'push "{str(local)}" "{remote_android_path}"')
        success = "pushed" in res.lower() or res.strip() == ""

        job = TransferJob(
            job_id=job_id,
            file_name=local.name,
            file_size_bytes=file_size,
            source_device="windows_host",
            target_device="android_phone",
            status="completed" if success else "failed",
            sha256=sha,
        )

        event_log.log_event(
            "file_transferred_to_device",
            source="file_transfer_engine",
            data={"file": local.name, "target": "android", "status": job.status},
        )
        logger.info("File '{}' ({}) transferred to Android ({})", local.name, file_size, job.status)
        return job

    def pull_from_android(self, remote_android_path: str, local_save_dir: str = "data/downloads") -> TransferJob:
        """Pull a file from Android phone to PC."""
        import time
        from mitchell.android.engine import android_engine

        save_dir = Path(local_save_dir).resolve()
        save_dir.mkdir(parents=True, exist_ok=True)
        file_name = Path(remote_android_path).name

        job_id = f"xfer_pull_{int(time.time()*1000)}"
        res = android_engine.adb.run_adb_command(f'pull "{remote_android_path}" "{str(save_dir)}"')

        dest_file = save_dir / file_name
        size = dest_file.stat().st_size if dest_file.exists() else 0

        job = TransferJob(
            job_id=job_id,
            file_name=file_name,
            file_size_bytes=size,
            source_device="android_phone",
            target_device="windows_host",
            status="completed" if dest_file.exists() else "failed",
        )
        return job


file_transfer_engine = FileTransferEngine()

__all__ = ["TransferJob", "FileTransferEngine", "file_transfer_engine"]
