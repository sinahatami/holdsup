"""The production guard: an API that would be wrong without failing refuses to start."""

from pathlib import Path

import pytest

from holdsup.config import Settings, get_settings, production_problems
from holdsup.main import create_app
from tests.telegram.fakes import SECRET, TOKEN

READY = {
    "app_env": "production",
    "database_url": "postgresql+asyncpg://u:p@db.example/holdsup",
    "trusted_proxies": 1,
    "web_origin": "https://holdsup.example",
    "telegram_bot_token": None,  # the bot is off unless a test turns it on
}


def settings(**changes: object) -> Settings:
    return Settings.model_validate({**READY, **changes})


def test_development_is_never_checked() -> None:
    dev = settings(app_env="development", database_url=None, trusted_proxies=0)
    assert production_problems(dev) == []


def test_a_complete_production_setup_passes() -> None:
    assert production_problems(settings()) == []
    bot = settings(telegram_bot_token=TOKEN, telegram_webhook_secret=SECRET)
    assert production_problems(bot) == []


@pytest.mark.parametrize(
    ("change", "named"),
    [
        ({"database_url": None}, "DATABASE_URL"),
        ({"trusted_proxies": 0}, "TRUSTED_PROXIES"),
        ({"web_origin": "http://localhost:3000"}, "WEB_ORIGIN"),
        ({"catalog_dir": Path("/nowhere/catalog")}, "CATALOG_DIR"),
        ({"telegram_bot_token": TOKEN}, "TELEGRAM_WEBHOOK_SECRET"),
        ({"telegram_bot_token": TOKEN, "telegram_webhook_secret": "short"},
         "TELEGRAM_WEBHOOK_SECRET"),
        ({"telegram_bot_token": TOKEN, "telegram_webhook_secret": SECRET + "\r"},
         "TELEGRAM_WEBHOOK_SECRET"),
        ({"telegram_bot_token": TOKEN + "\r", "telegram_webhook_secret": SECRET},
         "TELEGRAM_BOT_TOKEN"),
    ],
)  # fmt: skip
def test_each_gap_is_named(change: dict[str, object], named: str) -> None:
    problems = production_problems(settings(**change))
    assert len(problems) == 1
    assert problems[0].startswith(named)


def test_the_app_refuses_to_start_and_lists_every_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TRUSTED_PROXIES", "0")
    monkeypatch.setenv("WEB_ORIGIN", "http://localhost:3000")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(Settings, "model_config", {**Settings.model_config, "env_file": None})
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="Refusing to start in production") as caught:
        create_app()
    for name in ("DATABASE_URL", "TRUSTED_PROXIES", "WEB_ORIGIN"):
        assert name in str(caught.value)
