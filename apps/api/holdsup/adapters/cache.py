"""Reuse fetched series for 24 hours: `series_cache` in Postgres, keyed by source, code, filters."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from holdsup.adapters.base import FetchedSeries, Filters, Observation, SeriesAdapter
from holdsup.db.models import SeriesCacheEntry

TTL = timedelta(hours=24)


class Now(Protocol):
    def __call__(self) -> datetime: ...


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_filters(filters: Filters) -> dict[str, list[str]]:
    """Order-insensitive: keys sorted, list values sorted, single values as one-item lists."""
    out: dict[str, list[str]] = {}
    for key in sorted(filters):
        value = filters[key]
        out[key] = [value] if isinstance(value, str) else sorted(value)
    return out


def query_key(filters: Filters) -> str:
    blob = json.dumps(canonical_filters(filters), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


@dataclass(frozen=True)
class CachedSeries:
    source: str
    code: str
    query_key: str
    geo: str
    filters: dict[str, list[str]]
    retrieved_at: datetime
    raw_sha256: str
    rows: list[dict[str, object]]
    meta: dict[str, object]


def to_cached(series: FetchedSeries, filters: Filters) -> CachedSeries:
    canon = canonical_filters(filters)
    geos = canon.get("geo") or canon.get("country") or []
    return CachedSeries(
        source=series.source,
        code=series.dataset,
        query_key=query_key(filters),
        geo=",".join(geos),
        filters=canon,
        retrieved_at=series.retrieved_at,
        raw_sha256=series.raw_sha256,
        rows=[asdict(o) for o in series.observations],
        meta={
            "url": series.url,
            "label": series.label,
            "dimension_labels": series.dimension_labels,
            "status_labels": series.status_labels,
            "updated": series.updated,
            "unit": series.unit,
            "citation": series.citation,
        },
    )


def from_cached(entry: CachedSeries) -> FetchedSeries:
    meta = entry.meta

    def text(key: str) -> str | None:
        value = meta.get(key)
        return str(value) if value is not None else None

    observations = [
        Observation(
            geo=str(r["geo"]),
            period=str(r["period"]),
            value=float(cast(float, r["value"])) if r.get("value") is not None else None,
            status=str(r["status"]) if r.get("status") is not None else None,
            dims={str(k): str(v) for k, v in cast(Mapping[str, object], r.get("dims", {})).items()},
        )
        for r in entry.rows
    ]
    return FetchedSeries(
        source=entry.source,
        dataset=entry.code,
        url=text("url") or "",
        retrieved_at=entry.retrieved_at,
        raw_sha256=entry.raw_sha256,
        observations=observations,
        label=text("label") or "",
        dimension_labels=cast(dict[str, dict[str, str]], meta.get("dimension_labels") or {}),
        status_labels=cast(dict[str, str], meta.get("status_labels") or {}),
        updated=text("updated"),
        unit=text("unit"),
        citation=text("citation"),
    )


class SeriesCacheStore(Protocol):
    async def get(self, source: str, code: str, key: str) -> CachedSeries | None: ...

    async def put(self, entry: CachedSeries) -> None: ...


class InMemorySeriesCacheStore:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str, str], CachedSeries] = {}

    async def get(self, source: str, code: str, key: str) -> CachedSeries | None:
        return self.entries.get((source, code, key))

    async def put(self, entry: CachedSeries) -> None:
        self.entries[(entry.source, entry.code, entry.query_key)] = entry


class SqlSeriesCacheStore:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def get(self, source: str, code: str, key: str) -> CachedSeries | None:
        stmt = select(SeriesCacheEntry).where(
            SeriesCacheEntry.source == source,
            SeriesCacheEntry.code == code,
            SeriesCacheEntry.query_key == key,
        )
        async with self._sessionmaker() as session:
            row = await session.scalar(stmt)
        if row is None:
            return None
        return CachedSeries(
            source=row.source,
            code=row.code,
            query_key=row.query_key,
            geo=row.geo,
            filters=cast(dict[str, list[str]], row.filters),
            retrieved_at=row.retrieved_at,
            raw_sha256=row.raw_sha256,
            rows=row.rows,
            meta=row.meta,
        )

    async def put(self, entry: CachedSeries) -> None:
        values = {
            "source": entry.source,
            "code": entry.code,
            "query_key": entry.query_key,
            "geo": entry.geo,
            "filters": entry.filters,
            "retrieved_at": entry.retrieved_at,
            "raw_sha256": entry.raw_sha256,
            "rows": entry.rows,
            "meta": entry.meta,
        }
        stmt = insert(SeriesCacheEntry).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "code", "query_key"],
            set_={k: stmt.excluded[k] for k in values if k not in ("source", "code", "query_key")},
        )
        async with self._sessionmaker() as session, session.begin():
            await session.execute(stmt)


class CachedFetcher:
    """Fetch through the cache: a hit younger than `ttl` never calls the adapter."""

    def __init__(
        self,
        adapters: Mapping[str, SeriesAdapter],
        store: SeriesCacheStore,
        now: Now = utcnow,
        ttl: timedelta = TTL,
    ) -> None:
        self._adapters = adapters
        self._store = store
        self._now = now
        self._ttl = ttl

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        adapter = self._adapters.get(source)
        if adapter is None:
            raise KeyError(f"no adapter for source {source!r}")
        key = query_key(filters)
        hit = await self._store.get(source, dataset, key)
        if hit is not None and self._now() - hit.retrieved_at < self._ttl:
            return from_cached(hit)
        series = await adapter.fetch_series(dataset, filters)
        await self._store.put(to_cached(series, filters))
        return series
