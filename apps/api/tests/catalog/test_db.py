"""Loading into Postgres and pgvector search. Skipped unless TEST_DATABASE_URL is set."""

import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from holdsup.catalog.index import SqlIndex
from holdsup.catalog.load import sync
from holdsup.catalog.schema import Catalog, load_catalog
from holdsup.db.models import Indicator
from holdsup.db.url import to_async_url
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")


async def test_sync_loads_all_entries_and_search_ranks_them() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(to_async_url(TEST_DATABASE_URL))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    embedder = HashEmbedder()
    catalog = load_catalog(FIXTURE_CATALOG)
    try:
        assert await sync(catalog, embedder, sessionmaker) == 6
        assert await sync(catalog, embedder, sessionmaker) == 6  # idempotent upsert

        hits = await SqlIndex(sessionmaker).search(
            embedder.embed(["Life expectancy at birth"])[0], 3
        )
        assert hits[0].id == "life_expectancy"
        assert hits[0].score > hits[1].score

        smaller = Catalog(version="0.0.2-test", indicators=catalog.indicators[:2])
        assert await sync(smaller, embedder, sessionmaker) == 2
        async with sessionmaker() as s:
            assert await s.scalar(select(func.count()).select_from(Indicator)) == 2
            row = await s.get(Indicator, smaller.indicators[0].id)
            assert row is not None and row.catalog_version == "0.0.2-test"
    finally:
        await sync(Catalog(version="x", indicators=()), embedder, sessionmaker)
        await engine.dispose()
