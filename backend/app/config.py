from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    football_data_api_key: str = ""
    football_data_base_url: str = "https://api.football-data.org/v4"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/octopredict.db"
    database_sync_url: str = "sqlite:///./data/octopredict.db"

    # ML
    model_dir: str = "./data/models"
    min_training_samples: int = 50

    # Leagues to track
    leagues: list[str] = ["PL", "PD", "BL1", "SA"]
    seasons_to_fetch: int = 3

    # App
    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
