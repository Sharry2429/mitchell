"""Configuration module for Mitchell using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Mitchell application configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="MITCHELL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="mitchell",
        description="Name of the application",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory for application data and storage",
    )
    event_log_path: Path = Field(
        default=Path("data/events.jsonl"),
        description="Path to the JSONL event log file",
    )
    browser_headless: bool = Field(
        default=True,
        description="Run browser in headless mode by default",
    )
    browser_user_data_dir: Path = Field(
        default=Path("data/browser_profiles"),
        description="Base directory for persistent browser session profiles",
    )
    orb_host: str = Field(
        default="127.0.0.1",
        description="WebSocket bridge host for Electron Orb",
    )
    orb_port: int = Field(
        default=8765,
        description="WebSocket bridge port for Electron Orb",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
    return settings


# Global settings instance for easy import
settings: Settings = get_settings()
