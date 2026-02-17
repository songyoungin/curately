"""Application configuration loaded from config.yaml and environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML_PATH = PROJECT_ROOT / "config.yaml"


# --- YAML sub-models ---


class FeedConfig(BaseModel):
    """RSS feed entry."""

    name: str
    url: str


class ScheduleConfig(BaseModel):
    """Scheduler timing settings."""

    daily_pipeline_hour: int = 6
    daily_pipeline_minute: int = 0
    rewind_day_of_week: str = "sun"
    rewind_hour: int = 23
    rewind_minute: int = 0


class PipelineConfig(BaseModel):
    """Pipeline processing parameters."""

    relevance_threshold: float = 0.3
    max_articles_per_newsletter: int = 20
    scoring_batch_size: int = 10


class InterestsConfig(BaseModel):
    """Interest profile tuning parameters."""

    decay_factor: float = 0.9
    decay_interval_days: int = 7
    like_weight_increment: float = 1.0


class GeminiConfig(BaseModel):
    """Gemini model configuration."""

    model: str = "gemini-2.5-flash"


# --- Main settings ---


class Settings(BaseSettings):
    """Application settings combining .env secrets and config.yaml values."""

    # App config
    env: str = Field(default="dev")
    enable_internal_scheduler: bool = Field(default=True)
    cors_origins: str = Field(default="http://localhost:5173")

    # Secrets from .env
    gemini_api_key: str = Field(default="")
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_jwt_secret: str = Field(default="")

    # YAML-sourced config (populated via model_validator)
    feeds: list[FeedConfig] = Field(default_factory=list)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    interests: InterestsConfig = Field(default_factory=InterestsConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def __init__(self, **kwargs: Any) -> None:
        yaml_data = _load_yaml_config()
        merged = {**yaml_data, **kwargs}
        super().__init__(**merged)


def _load_yaml_config() -> dict[str, Any]:
    """Read and parse config.yaml, returning an empty dict on failure."""
    if not CONFIG_YAML_PATH.exists():
        return {}
    with CONFIG_YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
