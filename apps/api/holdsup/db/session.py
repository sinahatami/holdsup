"""Async engine and session factory. Nothing connects until a session is used."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from holdsup.config import get_settings
from holdsup.db.url import to_async_url


class DatabaseNotConfiguredError(RuntimeError):
    """DATABASE_URL is not set."""


def database_url() -> str:
    secret = get_settings().database_url
    if secret is None:
        raise DatabaseNotConfiguredError("DATABASE_URL is not set")
    return secret.get_secret_value()


@lru_cache
def get_engine() -> AsyncEngine:
    # pool_pre_ping: Neon suspends idle compute, so stale connections are expected.
    return create_async_engine(to_async_url(database_url()), pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: one session per request."""
    async with get_sessionmaker()() as session:
        yield session
