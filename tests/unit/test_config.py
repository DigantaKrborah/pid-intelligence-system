"""Settings / config tests."""
import pytest
from backend.config import Settings


def test_default_settings_have_required_fields():
    s = Settings(database_url="postgresql+asyncpg://u:p@localhost/db")
    assert s.api_port == 8000
    assert s.ollama_chat_model == "llama3.2"
    assert s.gemini_vision_model == "gemini-1.5-flash"
    assert s.max_upload_size_mb == 50


def test_cors_origins_list_splits_on_comma():
    s = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        cors_origins="http://localhost:8501,http://localhost:3000",
    )
    origins = s.cors_origins_list
    assert "http://localhost:8501" in origins
    assert "http://localhost:3000" in origins
    assert len(origins) == 2


def test_cors_origins_single_entry():
    s = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        cors_origins="http://localhost:8501",
    )
    assert s.cors_origins_list == ["http://localhost:8501"]


def test_is_development_flag():
    dev = Settings(database_url="postgresql+asyncpg://u:p@localhost/db", app_env="development")
    stg = Settings(database_url="postgresql+asyncpg://u:p@localhost/db", app_env="staging")
    assert dev.is_development is True
    assert stg.is_development is False


def test_settings_app_env_options():
    for env in ("development", "staging", "production", "test"):
        s = Settings(database_url="postgresql+asyncpg://u:p@localhost/db", app_env=env)
        assert s.app_env == env
