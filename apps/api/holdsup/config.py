"""Application settings, read from environment variables (never hard-coded secrets)."""

import re
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
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
    # The reranker export (D030): the image bakes it into /opt/reranker; locally, training or
    # `make reranker-fetch` puts it here. Its files must match holdsup/ml/reranker_pin.json.
    reranker_dir: Path = REPO_ROOT / "ml" / "reranker" / "artifacts" / "onnx"
    # New (not cached) checks per client address per hour.
    checks_per_hour: int = 10
    # Reports of a wrong match per client address per hour.
    reports_per_hour: int = 20
    # Article links read per client address per hour (each is one page fetch, cached or not).
    pages_per_hour: int = 20
    # Proxies in front of the API that append to X-Forwarded-For (0 = use the socket address).
    trusted_proxies: int = 0
    log_level: str = "INFO"
    # The git commit this build came from (the image build sets it); stamped on every receipt.
    app_commit: str = ""
    # The Telegram bot (off when no token): BotFather's token, and the secret Telegram sends
    # with every update so the webhook knows the call is Telegram's.
    telegram_bot_token: SecretStr | None = None
    telegram_webhook_secret: SecretStr | None = None

    @field_validator("telegram_bot_token", "telegram_webhook_secret", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        """`TELEGRAM_BOT_TOKEN=` (as in .env.example) means no bot, not an empty token; an
        empty secret would match an empty header."""
        return None if isinstance(value, str) and not value.strip() else value


# BotFather's token ("<bot id>:<35 characters>") and the secret setWebhook accepts.
TELEGRAM_TOKEN = re.compile(r"\d+:[A-Za-z0-9_-]{30,}")
TELEGRAM_SECRET = re.compile(r"[A-Za-z0-9_-]{16,256}")


def telegram_problems(settings: Settings) -> list[str]:
    """What would leave the Telegram bot unsafe or broken; empty when it is off (no token).
    Part of the production checks. Elsewhere the webhook stays off unless both are set
    (local development polls instead, which needs no secret)."""
    token, secret = settings.telegram_bot_token, settings.telegram_webhook_secret
    if token is None:
        return []
    problems = []
    if not TELEGRAM_TOKEN.fullmatch(token.get_secret_value()):
        problems.append(
            "TELEGRAM_BOT_TOKEN does not look like BotFather's token (digits, a colon, then "
            "letters, digits, - and _): check for a stray space or line break."
        )
    if secret is None or not TELEGRAM_SECRET.fullmatch(secret.get_secret_value()):
        problems.append(
            "TELEGRAM_WEBHOOK_SECRET must be set with the bot: 16 to 256 letters, digits, - "
            "and _ (`openssl rand -hex 32` makes one). Without it anyone could post updates."
        )
    return problems


def production_problems(settings: Settings) -> list[str]:
    """What would make a production API wrong without failing: empty unless APP_ENV is
    production. The app refuses to start while any remain (the image sets production)."""
    if settings.app_env != "production":
        return []
    problems = telegram_problems(settings)
    if settings.database_url is None:
        problems.append(
            "DATABASE_URL is not set: checks, the gallery and the daily provider budgets "
            "would live in memory and vanish on restart."
        )
    if settings.trusted_proxies < 1:
        problems.append(
            "TRUSTED_PROXIES is 0: behind the host's proxy every visitor would share one "
            "rate limit. Set it to the number of X-Forwarded-For entries the proxy adds "
            "(the `client_address` log line counts them; 1 is safe to start with)."
        )
    if not settings.web_origin.startswith("https://"):
        problems.append(
            f"WEB_ORIGIN is {settings.web_origin!r}: browsers on the site would be refused "
            "(CORS). Set it to the site's https address."
        )
    if not settings.catalog_dir.is_dir():
        problems.append(f"CATALOG_DIR {settings.catalog_dir} is not a folder.")
    return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
