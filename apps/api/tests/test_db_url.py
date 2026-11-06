import pytest

from holdsup.db.url import to_async_url


def test_neon_style_url_becomes_asyncpg_with_ssl() -> None:
    url = to_async_url(
        "postgres://user:pw@ep-x.eu-central-1.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    assert url.drivername == "postgresql+asyncpg"
    assert url.host == "ep-x.eu-central-1.aws.neon.tech"
    assert url.database == "neondb"
    assert dict(url.query) == {"ssl": "require"}


def test_plain_postgresql_url_without_ssl() -> None:
    url = to_async_url("postgresql://u:p@localhost:5432/holdsup")
    assert url.drivername == "postgresql+asyncpg"
    assert url.port == 5432
    assert dict(url.query) == {}


def test_asyncpg_url_is_kept_and_explicit_ssl_wins() -> None:
    url = to_async_url("postgresql+asyncpg://u:p@h/db?ssl=verify-full&sslmode=require")
    assert url.drivername == "postgresql+asyncpg"
    assert dict(url.query) == {"ssl": "verify-full"}


def test_other_drivers_are_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported database driver"):
        to_async_url("sqlite:///holdsup.db")
