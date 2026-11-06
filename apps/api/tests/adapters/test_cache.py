"""series_cache: 24-hour reuse; a cache hit never calls the adapter."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from holdsup.adapters.base import FetchedSeries, Filters, Observation
from holdsup.adapters.cache import (
    CachedFetcher,
    InMemorySeriesCacheStore,
    SqlSeriesCacheStore,
    canonical_filters,
    from_cached,
    query_key,
    to_cached,
)
from holdsup.db.models import SeriesCacheEntry
from holdsup.db.url import to_async_url

T0 = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def series(retrieved_at: datetime = T0) -> FetchedSeries:
    return FetchedSeries(
        source="fake",
        dataset="une_rt_a",
        url="https://example.invalid/une_rt_a",
        retrieved_at=retrieved_at,
        raw_sha256="ab" * 32,
        observations=[
            Observation("IT", "2024", 6.5, "p", {"unit": "PC_ACT"}),
            Observation("IT", "2025", None),
        ],
        label="Unemployment",
        dimension_labels={"geo": {"IT": "Italy"}},
        status_labels={"p": "provisional"},
        updated="2026-10-01",
        unit="%",
        citation="Eurostat (une_rt_a)",
    )


class CountingAdapter:
    source = "fake"

    def __init__(self, clock: "Clock") -> None:
        self.calls = 0
        self.clock = clock

    async def fetch_series(self, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls += 1
        return series(self.clock.t)


class Clock:
    def __init__(self) -> None:
        self.t = T0

    def __call__(self) -> datetime:
        return self.t


def fetcher() -> tuple[CachedFetcher, CountingAdapter, Clock]:
    clock = Clock()
    adapter = CountingAdapter(clock)
    return CachedFetcher({"fake": adapter}, InMemorySeriesCacheStore(), now=clock), adapter, clock


async def test_cache_hit_avoids_the_adapter_call() -> None:
    cached, adapter, clock = fetcher()
    first = await cached.fetch_series("fake", "une_rt_a", {"geo": ["IT", "DE"]})
    clock.t += timedelta(hours=23, minutes=59)
    second = await cached.fetch_series("fake", "une_rt_a", {"geo": ["DE", "IT"]})  # same query

    assert adapter.calls == 1
    assert second == first


async def test_entries_expire_after_24_hours() -> None:
    cached, adapter, clock = fetcher()
    await cached.fetch_series("fake", "une_rt_a", {"geo": "IT"})
    clock.t += timedelta(hours=24)
    refreshed = await cached.fetch_series("fake", "une_rt_a", {"geo": "IT"})
    assert adapter.calls == 2
    assert refreshed.retrieved_at == clock.t


async def test_different_filters_or_dataset_miss() -> None:
    cached, adapter, _ = fetcher()
    await cached.fetch_series("fake", "une_rt_a", {"geo": "IT"})
    await cached.fetch_series("fake", "une_rt_a", {"geo": "DE"})
    await cached.fetch_series("fake", "une_rt_m", {"geo": "IT"})
    assert adapter.calls == 3


async def test_unknown_source() -> None:
    cached, _, _ = fetcher()
    with pytest.raises(KeyError):
        await cached.fetch_series("nope", "x", {})


def test_round_trip_preserves_everything() -> None:
    original = series()
    entry = to_cached(original, {"geo": ["IT"], "unit": "PC_ACT"})
    assert entry.geo == "IT"
    assert from_cached(entry) == original


def test_query_key_ignores_order() -> None:
    assert canonical_filters({"geo": ["IT", "DE"], "a": "x"}) == {"a": ["x"], "geo": ["DE", "IT"]}
    assert query_key({"geo": ["IT", "DE"], "a": "x"}) == query_key(
        {"a": ["x"], "geo": ["DE", "IT"]}
    )
    assert query_key({"geo": "IT"}) != query_key({"geo": "DE"})


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")
async def test_sql_store_round_trip_and_upsert() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(to_async_url(TEST_DATABASE_URL))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    store = SqlSeriesCacheStore(sessionmaker)
    filters = {"geo": ["IT"]}
    try:
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(SeriesCacheEntry).where(SeriesCacheEntry.source == "fake"))

        assert await store.get("fake", "une_rt_a", query_key(filters)) is None
        await store.put(to_cached(series(), filters))
        newer = series(T0 + timedelta(days=2))
        await store.put(to_cached(newer, filters))  # upsert, not a duplicate

        got = await store.get("fake", "une_rt_a", query_key(filters))
        assert got is not None
        assert from_cached(got) == newer
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(SeriesCacheEntry).where(SeriesCacheEntry.source == "fake"))
        await engine.dispose()
