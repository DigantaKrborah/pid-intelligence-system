"""
config.py — Application settings
Reads all configuration values from the backend/.env file.
Uses pydantic-settings so missing required values cause a clear error at startup.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Path to the .env file — it lives in /backend/, three levels up from this file
_ENV_FILE = str(Path(__file__).parent.parent.parent / ".env")


class Settings(BaseSettings):
    """All application settings. Values come from backend/.env"""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",           # ignore any extra keys in .env
    )

    # --- Database ---
    database_url: str             # e.g. postgresql://postgres:pass@localhost:5432/pid_system

    # --- File storage (local only) ---
    upload_base_path: str = "E:/PID_Reader/uploads"

    # --- Authentication ---
    jwt_secret: str = ""          # must be filled in .env before running
    jwt_expire_hours: int = 8

    # --- CORS (comma-separated list of allowed frontend origins) ---
    # Example: http://localhost:5173,http://192.168.1.100:5173
    cors_origins: str = "http://localhost:5173"

    # --- AI provider ---
    default_llm_provider: str = "claude"   # claude | openai | gemini

    # --- LLM API keys (env-var fallback for when DB settings aren't configured yet) ---
    gemini_api_key:    Optional[str] = None   # GEMINI_API_KEY in .env
    openai_api_key:    Optional[str] = None   # OPENAI_API_KEY in .env
    anthropic_api_key: Optional[str] = None   # ANTHROPIC_API_KEY in .env

    # --- PDF processing ---
    # Leave unset (None) when running in Docker — Poppler is on the system PATH.
    # Set to the Poppler bin directory only for local Windows installs.
    poppler_path: Optional[str] = None


@lru_cache          # call get_settings() anywhere — it only creates the object once
def get_settings() -> Settings:
    """Return the application settings (cached after first call)."""
    return Settings()
