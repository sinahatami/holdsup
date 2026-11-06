import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from holdsup.db.session import (
    DatabaseNotConfiguredError,
    get_engine,
    get_session,
    get_sessionmaker,
)


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir("/")  # no .env file to pick up
    with pytest.raises(DatabaseNotConfiguredError):
        get_engine()


def test_engine_uses_database_url_and_hides_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:secret@db.example/holdsup?sslmode=require")
    engine = get_engine()
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.database == "holdsup"
    assert "secret" not in repr(engine.url)
    assert get_engine() is engine


async def test_get_session_yields_a_session_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example/holdsup")
    sessions = get_session()
    session = await anext(sessions)
    assert isinstance(session, AsyncSession)
    assert session.bind is get_sessionmaker().kw["bind"]
    await sessions.aclose()
