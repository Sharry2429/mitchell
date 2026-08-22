"""Media Worker Agent executing music, playback, video download, and download queue tasks."""

import json
from typing import Any, Dict, Union

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.media import (
    download_manager,
    media_player,
    media_recommender,
    spotify_controller,
    video_downloader,
)


class MediaWorkerAgent(BaseAgent):
    """Hive Agent specializing in media playback, Spotify search, and high-speed downloading."""

    def __init__(
        self,
        agent_id: str = "media_worker",
        description: str = "Controls music playback, Spotify, YouTube extraction, and download queues",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process media task."""
        logger.info("MediaWorker received task from {}: {}", sender, message)

        if isinstance(message, dict):
            action = message.get("action", "")
            data = message
        else:
            text = str(message).strip()
            parts = text.split(maxsplit=1)
            action = parts[0].lower() if parts else ""
            data = {"raw": parts[1]} if len(parts) > 1 else {}

        event_log.log_event(
            "media_worker_task_started",
            source=self.agent_id,
            data={"action": action, "sender": sender},
        )

        try:
            if action in ("spotify", "play_music", "play"):
                query = data.get("query") or data.get("raw") or "relaxing music"
                res = spotify_controller.play_track(query_or_uri=query)
                return {"status": "success", "result": res}

            elif action in ("download_video", "youtube"):
                url = data.get("url") or data.get("raw") or ""
                res = video_downloader.download_video(video_url=url)
                return {"status": "success", "result": res}

            elif action in ("download", "queue_download"):
                url = data.get("url") or data.get("raw") or ""
                item = download_manager.add_download(url=url)
                return {"status": "success", "download_id": item.id, "file_name": item.file_name}

            elif action in ("status", "playback_status"):
                return {"status": "success", "playback": media_player.get_state()}

            return {"status": "success", "message": f"Media task executed: {message}"}

        except Exception as e:
            logger.error("MediaWorker error: {}", e)
            return {"status": "error", "error": str(e)}


__all__ = ["MediaWorkerAgent"]
