from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-1.5-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # Database
    database_url: str = "postgresql+asyncpg://pid_user:dev_password@localhost:5432/pid_intelligence"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Storage
    upload_dir: str = "./data/pids"
    manuals_dir: str = "./data/manuals"
    graph_dir: str = "./data/graphs"
    max_upload_size_mb: int = 50

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:8501"
    secret_key: str = "dev-secret-key"

    # GitHub (bug reporting)
    github_token: str = ""
    github_repo: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
