"""SqlUsageStore against a real Postgres. Skipped unless TEST_DATABASE_URL is set
(e.g. a local `pgvector/pgvector` container migrated with `alembic upgrade head`)."""

import os
from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from holdsup.db.models import ProviderUsage
from holdsup.db.url import to_async_url
from holdsup.router.budgets import SqlUsageStore

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")


async def test_record_upserts_and_counts_per_day() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(to_async_url(TEST_DATABASE_URL))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    store = SqlUsageStore(sessionmaker)
    day, other = date(2026, 11, 6), date(2026, 11, 7)
    try:
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(ProviderUsage).where(ProviderUsage.provider == "test-provider"))

        assert await store.requests_on("test-provider", day) == 0
        await store.record("test-provider", day, tokens=10)
        await store.record("test-provider", day, tokens=5)
        await store.record("test-provider", other, tokens=1)
        await store.add_tokens("test-provider", day, 100)

        assert await store.requests_on("test-provider", day) == 2
        assert await store.requests_on("test-provider", other) == 1
        async with sessionmaker() as s:
            row = await s.get(ProviderUsage, ("test-provider", day))
            assert row is not None
            assert row.tokens == 115
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(ProviderUsage).where(ProviderUsage.provider == "test-provider"))
        await engine.dispose()
