from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANREVIEW_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8765
    base_dir: Path = Path.home() / "Library" / "Application Support" / "PlanReview"

    @property
    def db_path(self) -> Path:
        return self.base_dir / "planreview.sqlite3"

    @property
    def projects_dir(self) -> Path:
        return self.base_dir / "projects"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.base_dir.mkdir(parents=True, exist_ok=True)
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    return settings
