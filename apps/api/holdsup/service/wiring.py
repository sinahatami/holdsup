"""Build the real check runner: Postgres, the embedding model, the data sources, the router.

Nothing here connects or loads a model at import; `build_runner` runs on the first request
that needs it (the routes' `get_runner` dependency).
"""

from dataclasses import dataclass

import httpx

from holdsup.adapters.cache import CachedFetcher, SqlSeriesCacheStore
from holdsup.adapters.registry import build_adapters
from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import SqlIndex
from holdsup.catalog.schema import load_catalog
from holdsup.config import Settings
from holdsup.db.session import get_sessionmaker
from holdsup.pipeline.ledger import Ledger
from holdsup.pipeline.match import vector_search
from holdsup.pipeline.run import Pipeline
from holdsup.router import Router, load_router_config
from holdsup.router.budgets import SqlUsageStore
from holdsup.router.client import OpenAICompatibleClient
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner
from holdsup.service.store import SqlCheckStore
from holdsup.verdict import load_tolerances

HOUR_S = 3600.0


@dataclass
class Built:
    runner: CheckRunner
    http: httpx.AsyncClient

    async def close(self) -> None:
        await self.runner.shutdown()
        await self.http.aclose()


def build_runner(settings: Settings) -> Built:  # pragma: no cover (needs Postgres + model)
    sessionmaker = get_sessionmaker()
    embedder = default_embedder(settings.fastembed_cache_path)
    http = httpx.AsyncClient(timeout=30.0)
    fetcher = CachedFetcher(build_adapters(http), SqlSeriesCacheStore(sessionmaker))
    pipeline = Pipeline(
        router=Router(load_router_config(), OpenAICompatibleClient(), SqlUsageStore(sessionmaker)),
        catalog=load_catalog(settings.catalog_dir),
        search=vector_search(SqlIndex(sessionmaker).search, embedder),
        fetcher=fetcher,
        tolerances=load_tolerances(),
    )
    store = SqlCheckStore(sessionmaker)
    runner = CheckRunner(
        store=store,
        ledger=Ledger(store, embedder, versions=pipeline.versions()),
        pipeline=pipeline,
        limiter=RateLimiter(settings.checks_per_hour, HOUR_S),
    )
    return Built(runner, http)
