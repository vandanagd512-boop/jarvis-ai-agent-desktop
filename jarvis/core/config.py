"""Configuration management for JARVIS AI Desktop Assistant.

Loads settings from environment variables, .env file, and defaults.
Uses Pydantic Settings for strict typing and validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for JARVIS."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General Application
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "testing"] = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Base Paths
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data")
    LOG_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "logs")
    PLUGINS_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "plugins")

    # Database
    DATABASE_URL: str = ""

    # Brain & Reasoning Providers
    DEFAULT_LLM_PROVIDER: Literal["gemini", "openai", "offline"] = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 4096
    FALLBACK_TO_OFFLINE: bool = True

    # Voice & Audio
    WAKE_WORD: str = "jarvis"
    WAKE_WORD_SENSITIVITY: float = 0.5
    VOICE_ENGINE: str = "sapi5"  # Windows native TTS
    VOICE_RATE: int = 185
    VOICE_VOLUME: float = 1.0
    VOICE_GENDER: Literal["male", "female"] = "male"
    STT_ENERGY_THRESHOLD: int = 300
    STT_PAUSE_THRESHOLD: float = 0.8
    CONTINUOUS_LISTENING: bool = True

    # Windows Automation & Control
    SAFE_MODE: bool = True
    MAX_COMMAND_TIMEOUT_SECONDS: int = 30
    ALLOW_CODE_EXECUTION: bool = True
    ALLOW_SYSTEM_POWER_COMMANDS: bool = True

    # Productivity & Messaging
    EMAIL_SMTP_SERVER: str = ""
    EMAIL_SMTP_PORT: int = 587
    EMAIL_IMAP_SERVER: str = ""
    EMAIL_IMAP_PORT: int = 993
    EMAIL_ADDRESS: str = ""
    EMAIL_PASSWORD: str = ""

    # API Server (Internal Desktop Control / GUI)
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8765

    def ensure_directories(self) -> None:
        """Create necessary system directories if they don't exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "screenshots").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "notes").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "audio").mkdir(parents=True, exist_ok=True)

    @property
    def effective_database_url(self) -> str:
        """Return database URL or default SQLite path."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        db_path = self.DATA_DIR / "jarvis.db"
        return f"sqlite:///{db_path.as_posix()}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached singleton settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
