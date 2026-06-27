from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://propguard:propguard@postgres:5432/propguard"
    redis_url: str = "redis://redis:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]
    google_maps_api_key: str | None = None
    tgos_app_id: str | None = None
    tgos_api_key: str | None = None


settings = Settings()
