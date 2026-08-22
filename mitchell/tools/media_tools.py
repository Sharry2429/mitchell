"""Media tools for the Mitchell ToolRegistry exposing playback, Spotify, and downloads."""

import json
from typing import Any, Dict, List, Optional

from mitchell.media import download_manager, media_player, media_recommender, spotify_controller, video_downloader
from mitchell.tools.registry import Tool


def tool_media_play_spotify(query: str) -> str:
    """Search and play a song, album, or artist on Spotify."""
    res = spotify_controller.play_track(query_or_uri=query)
    return json.dumps(res)


def tool_media_download_video(url: str) -> str:
    """Download highest-quality video or audio from YouTube and web video platforms."""
    res = video_downloader.download_video(video_url=url)
    return json.dumps(res)


def tool_media_add_download(url: str, file_name: Optional[str] = None) -> str:
    """Queue a file download in the high-speed download manager."""
    item = download_manager.add_download(url=url, file_name=file_name)
    return f"Queued download: '{item.file_name}' (ID: {item.id})"


# Tool definitions
spotify_tool = Tool(
    name="media_play_spotify",
    description="Search for and start playing music on Spotify.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Track title, album name, or artist"},
        },
        "required": ["query"],
    },
    function=tool_media_play_spotify,
)

video_download_tool = Tool(
    name="media_download_video",
    description="Download a video from YouTube or web URLs to local files.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Video URL to download"},
        },
        "required": ["url"],
    },
    function=tool_media_download_video,
)

download_tool = Tool(
    name="media_queue_download",
    description="Queue a high-speed multi-connection file download.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Direct file download URL"},
            "file_name": {"type": "string", "description": "Optional custom file name"},
        },
        "required": ["url"],
    },
    function=tool_media_add_download,
)

TOOLS = [
    spotify_tool,
    video_download_tool,
    download_tool,
]
