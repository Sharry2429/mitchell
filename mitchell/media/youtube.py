"""YouTube and multi-provider video extraction and downloading."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class VideoDownloader:
    """Extracts and downloads highest-quality MP4/MP3 media from YouTube and web video providers."""

    def download_video(
        self,
        video_url: str,
        output_format: str = "mp4",
        save_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Download video to MP4 / best quality."""
        target_dir = Path(save_dir or settings.download_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        yt_dlp_bin = shutil.which("yt-dlp")
        if not yt_dlp_bin:
            # Fallback message
            return {
                "status": "info",
                "message": "yt-dlp CLI utility not detected in PATH. Please run 'pip install yt-dlp' or place binary in PATH.",
                "url": video_url,
            }

        cmd = [
            yt_dlp_bin,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", str(target_dir / "%(title)s.%(ext)s"),
            video_url,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            event_log.log_event(
                "video_downloaded",
                source="video_downloader",
                data={"url": video_url, "code": res.returncode},
            )
            return {
                "status": "success" if res.returncode == 0 else "error",
                "output": res.stdout,
                "error": res.stderr if res.returncode != 0 else None,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


video_downloader = VideoDownloader()

__all__ = ["VideoDownloader", "video_downloader"]
