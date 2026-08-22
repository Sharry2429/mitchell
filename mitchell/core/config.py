"""Configuration module for Mitchell using pydantic-settings.

Expanded for Final Peak specification — covers all subsystems:
providers, workspace, studio, cross-device, media, commerce, IoT, and comms.
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Mitchell application configuration settings — Final Peak edition."""

    model_config = SettingsConfigDict(
        env_prefix="MITCHELL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Core ──────────────────────────────────────────────────────────────
    app_name: str = Field(default="mitchell", description="Name of the application")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    data_dir: Path = Field(default=Path("data"), description="Directory for application data and storage")
    event_log_path: Path = Field(default=Path("data/events.jsonl"), description="Path to the JSONL event log file")

    # ── Browser Pillar ────────────────────────────────────────────────────
    browser_headless: bool = Field(default=True, description="Run browser in headless mode by default")
    browser_user_data_dir: Path = Field(
        default=Path("data/browser_profiles"),
        description="Base directory for persistent browser session profiles",
    )

    # ── Orb ───────────────────────────────────────────────────────────────
    orb_host: str = Field(default="127.0.0.1", description="WebSocket bridge host for Electron Orb")
    orb_port: int = Field(default=8765, description="WebSocket bridge port for Electron Orb")

    # ── Studio Command Center ─────────────────────────────────────────────
    studio_host: str = Field(default="127.0.0.1", description="Studio server bind address")
    studio_port: int = Field(default=8500, description="Studio server port")
    studio_ws_port: int = Field(default=8501, description="Studio WebSocket streaming port")
    studio_secret: str = Field(default="", description="Optional session secret for Studio auth")

    # ── Provider Cascade ──────────────────────────────────────────────────
    provider_cascade: str = Field(
        default="groq,nvidia_nim,openrouter,deepseek,openai,anthropic,gemini",
        description="Comma-separated provider priority order (first = highest priority)",
    )
    free_tier_first: bool = Field(
        default=True,
        description="Always try free-tier providers before paid ones",
    )
    provider_timeout: float = Field(default=30.0, description="HTTP timeout per provider call in seconds")
    provider_max_retries: int = Field(default=2, description="Max retries on provider failure before fallback")

    # Provider API keys (read from env without MITCHELL_ prefix too)
    groq_api_key: str = Field(default="", description="Groq API key")
    nvidia_nim_api_key: str = Field(default="", description="NVIDIA NIM API key")
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    deepseek_api_key: str = Field(default="", description="DeepSeek API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    xai_api_key: str = Field(default="", description="xAI (Grok) API key")

    # ── Workspace ─────────────────────────────────────────────────────────
    workspace_root: Path = Field(
        default=Path("data/workspace"),
        description="Root directory for Mitchell native workspace",
    )
    workspace_versioning: bool = Field(default=True, description="Enable file versioning in workspace")
    workspace_max_versions: int = Field(default=50, description="Max version history per file")

    # ── Cross-Device Sync ─────────────────────────────────────────────────
    sync_enabled: bool = Field(default=False, description="Enable cross-device sync")
    sync_port: int = Field(default=8600, description="LAN sync WebSocket port")
    sync_encryption_key: str = Field(default="", description="Encryption key for sync payloads (auto-generated if empty)")
    sync_discovery_port: int = Field(default=8601, description="mDNS/UDP discovery port for LAN pairing")

    # ── Media & Entertainment ─────────────────────────────────────────────
    spotify_client_id: str = Field(default="", description="Spotify Web API client ID")
    spotify_client_secret: str = Field(default="", description="Spotify Web API client secret")
    spotify_redirect_uri: str = Field(default="http://127.0.0.1:8500/callback/spotify", description="Spotify OAuth redirect")
    download_dir: Path = Field(default=Path("data/downloads"), description="Default download directory")
    download_max_connections: int = Field(default=8, description="Max parallel connections per download")
    download_max_concurrent: int = Field(default=3, description="Max concurrent downloads")

    # ── Commerce ──────────────────────────────────────────────────────────
    commerce_cache_dir: Path = Field(default=Path("data/commerce_cache"), description="Cache for product/price data")
    commerce_price_check_interval_hours: int = Field(default=6, description="Hours between automatic price checks")

    # ── IoT / Home Assistant ──────────────────────────────────────────────
    homeassistant_url: str = Field(default="", description="Home Assistant base URL (e.g. http://192.168.1.100:8123)")
    homeassistant_token: str = Field(default="", description="Home Assistant Long-Lived Access Token")

    # ── Communication Hub ─────────────────────────────────────────────────
    email_imap_host: str = Field(default="", description="IMAP server for email reading")
    email_imap_port: int = Field(default=993, description="IMAP port (SSL)")
    email_smtp_host: str = Field(default="", description="SMTP server for sending email")
    email_smtp_port: int = Field(default=587, description="SMTP port (TLS)")
    email_address: str = Field(default="", description="Email address")
    email_password: str = Field(default="", description="Email password / app password")

    # ── Voice ─────────────────────────────────────────────────────────────
    voice_wake_word: str = Field(default="hey mitchell", description="Wake word for voice activation")
    voice_stt_provider: str = Field(default="groq", description="STT provider: groq, whisper_local, openai")
    voice_tts_provider: str = Field(default="system", description="TTS provider: system, openai, elevenlabs")
    voice_duplex: bool = Field(default=True, description="Enable full-duplex voice (listen while speaking)")

    # ── Research ──────────────────────────────────────────────────────────
    research_max_parallel_sources: int = Field(default=5, description="Max parallel browser tabs for research")
    research_save_to_workspace: bool = Field(default=True, description="Auto-save research findings to workspace")

    # ── Android / Cross-Device ────────────────────────────────────────────
    adb_host: str = Field(default="", description="ADB wireless host (IP:port)")
    scrcpy_path: str = Field(default="scrcpy", description="Path to scrcpy binary")
    phone_link_enabled: bool = Field(default=True, description="Use Windows Phone Link integration when available")

    @property
    def provider_cascade_list(self) -> List[str]:
        """Return provider cascade as a list."""
        return [p.strip() for p in self.provider_cascade.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.commerce_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings


# Global settings instance for easy import
settings: Settings = get_settings()
