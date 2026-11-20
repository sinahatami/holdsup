"""Build the real check runner: Postgres, the embedding model, the reranker, the data sources,
the router.

Nothing here connects or loads a model at import; `build_runner` runs on the first request
that needs it (the routes' `get_runner` dependency).
"""

from dataclasses import dataclass
from pathlib import Path

import httpx
import structlog

from holdsup.adapters.cache import CachedFetcher, SqlSeriesCacheStore
from holdsup.adapters.registry import build_adapters
from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import IndicatorHit, SqlIndex
from holdsup.catalog.schema import load_catalog
from holdsup.catalog.search import vector_search
from holdsup.config import Settings
from holdsup.db.session import get_sessionmaker
from holdsup.ml.confidence import MODEL_FILE, ConfidenceModel, load_confidence
from holdsup.ml.reranker import OnnxReranker, load_reranker
from holdsup.pipeline.ledger import Ledger
from holdsup.pipeline.run import Pipeline
from holdsup.pipeline.steps import CodeSteps
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
        confidence=optional_confidence(),
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


def optional_confidence(path: Path = MODEL_FILE) -> ConfidenceModel | None:
    """The trained confidence model, or None (logged) before the first one is trained: claims
    then carry their signals with no confidence label and nothing is withheld."""
    model = load_confidence(path)
    if model is None:
        log.info(
            "confidence_model_missing",
            file=str(path),
            hint="make eval, then make confidence-train",
        )
    return model


@dataclass
class WatchParts:
    """What the claim watch (S1) needs: the store and the code's steps over the data sources."""

    store: SqlCheckStore
    steps: CodeSteps  # a Pipeline (with the router) for the backfill
    http: httpx.AsyncClient

    async def close(self) -> None:
        await self.http.aclose()


async def _never_search(phrase: str, k: int) -> list[IndicatorHit]:
    raise RuntimeError("the claim watch never matches a claim to a statistic")


def build_watch(settings: Settings, *, planner: bool = False) -> WatchParts:  # pragma: no cover
    """The claim watch's parts: Postgres, the data sources, the catalog and tolerances. No
    embedding model, reranker or router (no provider key needed), except for the backfill
    (`planner`), which asks the plan model through the router."""
    sessionmaker = get_sessionmaker()
    http = httpx.AsyncClient(timeout=30.0)
    fetcher = CachedFetcher(build_adapters(http), SqlSeriesCacheStore(sessionmaker))
    catalog, tolerances = load_catalog(settings.catalog_dir), load_tolerances()
    steps: CodeSteps
    if planner:
        steps = Pipeline(
            router=Router(
                load_router_config(), OpenAICompatibleClient(), SqlUsageStore(sessionmaker)
            ),
            search=_never_search,
            catalog=catalog,
            fetcher=fetcher,
            tolerances=tolerances,
            confidence=optional_confidence(),
        )
    else:
        steps = CodeSteps(
            catalog=catalog,
            fetcher=fetcher,
            tolerances=tolerances,
            confidence=optional_confidence(),
        )
    return WatchParts(SqlCheckStore(sessionmaker), steps, http)
