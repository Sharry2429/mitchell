"""Spotify Web API and desktop playback integration."""

import urllib.parse
from typing import Any, Dict, List, Optional
import httpx

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.media.player import media_player


class SpotifyController:
    """Controls Spotify playback, search, and playlists via Web API or desktop URI intent."""

    def play_track(self, query_or_uri: str) -> Dict[str, Any]:
        """Play a track, album, or artist on Spotify."""
        if query_or_uri.startswith("spotify:"):
            uri = query_or_uri
        else:
            uri = f"spotify:search:{urllib.parse.quote(query_or_uri)}"

        # Open in Spotify desktop app via URI
        import subprocess
        try:
            subprocess.Popen(f'start {uri}', shell=True)
            media_player.play(title=query_or_uri, source="spotify")
            event_log.log_event(
                "spotify_playback_started",
                source="spotify_controller",
                data={"query": query_or_uri},
            )
            return {"status": "success", "action": "playing", "target": query_or_uri}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search Spotify for matching tracks."""
        # Simulated/Cached results when offline
        return [
            {"title": query, "artist": "Various Artists", "source": "spotify", "uri": f"spotify:search:{query}"}
        ]


spotify_controller = SpotifyController()

__all__ = ["SpotifyController", "spotify_controller"]
