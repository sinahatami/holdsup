"""Application settings, read from environment variables (never hard-coded secrets)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    web_origin: str = "http://localhost:3000"
    database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
