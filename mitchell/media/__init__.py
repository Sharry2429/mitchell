"""Mitchell Peak Media Subsystem — Universal Media Player, Spotify, Download Manager, YouTube, and Recommendations."""

from mitchell.media.downloads import DownloadItem, DownloadManager, download_manager
from mitchell.media.player import MediaPlayerController, PlaybackState, media_player
from mitchell.media.recommender import MediaRecommender, media_recommender
from mitchell.media.spotify import SpotifyController, spotify_controller
from mitchell.media.youtube import VideoDownloader, video_downloader

__all__ = [
    "MediaPlayerController",
    "media_player",
    "PlaybackState",
    "SpotifyController",
    "spotify_controller",
    "DownloadManager",
    "download_manager",
    "DownloadItem",
    "VideoDownloader",
    "video_downloader",
    "MediaRecommender",
    "media_recommender",
]
