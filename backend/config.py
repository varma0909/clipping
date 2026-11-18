from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "qwen2.5:3b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    whisper_model: str = "small"
    max_video_hours: float = 3
    retention_hours: int = 24
    storage_dir: str = "storage"
    frontend_origins: str = "http://localhost:3000,http://localhost:3001"
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        if not path.is_absolute():
            path = Path(__file__).parent / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
