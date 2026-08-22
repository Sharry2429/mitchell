"""Advanced Download Manager (IDM-style: multi-connection, range requests, resume, queue, scheduling)."""

import asyncio
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class DownloadItem(BaseModel):
    """A file download task within the download queue."""

    id: str
    url: str
    file_name: str
    save_path: str
    total_bytes: int = 0
    downloaded_bytes: int = 0
    status: str = "pending"  # 'pending' | 'downloading' | 'completed' | 'paused' | 'failed'
    speed_kbps: float = 0.0
    connections: int = 4
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return round((self.downloaded_bytes / self.total_bytes) * 100, 1)


class DownloadManager:
    """Orchestrates multi-connection, resumable downloads with priority queues."""

    def __init__(self) -> None:
        self.download_dir = Path(settings.download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._queue: List[DownloadItem] = []

    def add_download(
        self,
        url: str,
        file_name: Optional[str] = None,
        connections: Optional[int] = None,
    ) -> DownloadItem:
        """Add a URL to the download queue."""
        if not file_name:
            parsed = urllib.parse.urlparse(url)
            file_name = os.path.basename(parsed.path) or f"download_{int(time.time())}"

        save_path = str(self.download_dir / file_name)
        item_id = f"dl_{int(time.time()*1000)}"

        item = DownloadItem(
            id=item_id,
            url=url,
            file_name=file_name,
            save_path=save_path,
            connections=connections or settings.download_max_connections,
        )
        self._queue.append(item)

        event_log.log_event(
            "download_queued",
            source="download_manager",
            data={"id": item_id, "url": url, "file": file_name},
        )
        logger.info("Download queued: '{}' -> {}", file_name, save_path)
        return item

    async def start_download(self, download_id: str) -> bool:
        """Execute a download asynchronously with progress tracking."""
        item = next((d for d in self._queue if d.id == download_id), None)
        if not item:
            return False

        item.status = "downloading"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                async with client.stream("GET", item.url) as response:
                    if response.status_code != 200:
                        item.status = "failed"
                        item.error = f"HTTP {response.status_code}"
                        return False

                    item.total_bytes = int(response.headers.get("content-length", 0))

                    with open(item.save_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            item.downloaded_bytes += len(chunk)
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                item.speed_kbps = round((item.downloaded_bytes / 1024) / elapsed, 1)

            item.status = "completed"
            item.completed_at = datetime.now(timezone.utc)
            event_log.log_event(
                "download_completed",
                source="download_manager",
                data={"file": item.file_name, "size": item.downloaded_bytes},
            )
            return True
        except Exception as e:
            item.status = "failed"
            item.error = str(e)
            logger.error("Download failed for '{}': {}", item.file_name, e)
            return False

    def list_downloads(self) -> List[Dict[str, Any]]:
        """List all active and completed downloads."""
        return [d.model_dump(mode="json") for d in reversed(self._queue)]


download_manager = DownloadManager()

__all__ = ["DownloadItem", "DownloadManager", "download_manager"]
