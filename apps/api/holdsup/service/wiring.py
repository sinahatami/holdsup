"""Build the real check runner: Postgres, the embedding model, the reranker, the data sources,
the router.

Nothing here connects or loads a model at import; `build_runner` runs on the first request
that needs it (the routes' `get_runner` dependency).
"""

from dataclasses import dataclass

import httpx
import structlog

from holdsup.adapters.cache import CachedFetcher, SqlSeriesCacheStore
from holdsup.adapters.registry import build_adapters
from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import SqlIndex
from holdsup.catalog.schema import load_catalog
from holdsup.catalog.search import vector_search
from holdsup.config import Settings
from holdsup.db.session import get_sessionmaker
from holdsup.ml.reranker import OnnxReranker, load_reranker
from holdsup.pipeline.ledger import Ledger
from holdsup.pipeline.run import Pipeline
from holdsup.router import Router, load_router_config
from holdsup.router.budgets import SqlUsageStore
from holdsup.router.client import OpenAICompatibleClient
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner
from holdsup.service.store import SqlCheckStore
from holdsup.verdict import load_tolerances

HOUR_S = 3600.0

log = structlog.get_logger(__name__)


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
        reranker=optional_reranker(settings),
    )
    store = SqlCheckStore(sessionmaker)
    runner = CheckRunner(
        store=store,
        ledger=Ledger(store, embedder, versions=pipeline.versions()),
        pipeline=pipeline,
        limiter=RateLimiter(settings.checks_per_hour, HOUR_S),
    )
    return Built(runner, http)


def optional_reranker(settings: Settings) -> OnnxReranker | None:
    """The pinned reranker, or None (with a warning) when its folder is absent, as in a fresh
    clone: matching then asks the model every time. Files that are there but not the pinned
    ones raise `RerankerFilesError`: a model the skip margin was not tuned for is worse than
    none. The image always has the folder (its build checks the files)."""
    if not settings.reranker_dir.is_dir():
        log.warning(
            "reranker_missing",
            folder=str(settings.reranker_dir),
            hint="make reranker-fetch; until then the match model picks every indicator",
        )
        return None
    return load_reranker(settings.reranker_dir)
