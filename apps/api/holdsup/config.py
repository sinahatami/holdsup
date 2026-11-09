"""Application settings, read from environment variables (never hard-coded secrets)."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    web_origin: str = "http://localhost:3000"
    database_url: SecretStr | None = None
    catalog_dir: Path = REPO_ROOT / "packages" / "catalog"
    # Where fastembed keeps the embedding model; None = fastembed's default temp dir.
    fastembed_cache_path: str | None = None
    # New (not cached) checks per client address per hour.
    checks_per_hour: int = 10
    # Reports of a wrong match per client address per hour.
    reports_per_hour: int = 20
    # Proxies in front of the API that append to X-Forwarded-For (0 = use the socket address).
    trusted_proxies: int = 0
    log_level: str = "INFO"
    # The git commit this build came from (the image build sets it); stamped on every receipt.
    app_commit: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
