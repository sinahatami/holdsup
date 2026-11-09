"""What route handlers depend on: the check runner, the check store and the catalog search.

Handlers take these as `Annotated` parameters (`Runner`, `Store`, `Search`) and never build them.
Tests swap the providers with `app.dependency_overrides`; nothing here connects at import.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import SqlIndex
from holdsup.catalog.schema import Catalog, load_catalog
from holdsup.catalog.search import CatalogSearch, vector_search
from holdsup.config import get_settings
from holdsup.db.session import get_sessionmaker
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner
from holdsup.service.store import CheckStore, SqlCheckStore
from holdsup.service.wiring import HOUR_S, build_runner
from holdsup.verdict import Tolerances, load_tolerances


def get_runner(request: Request) -> CheckRunner:
    """The app's runner, built on first use (it loads the embedding model)."""
    state = request.app.state
    if getattr(state, "built", None) is None:  # pragma: no cover (tests override this)
        state.built = build_runner(get_settings())
    runner: CheckRunner = state.built.runner
    return runner


def get_store() -> CheckStore:  # pragma: no cover (tests override this)
    """Reads need no runner, so the gallery loads without the embedding model."""
    return SqlCheckStore(get_sessionmaker())


def get_catalog_search() -> CatalogSearch:  # pragma: no cover (tests override this)
    embedder = default_embedder(get_settings().fastembed_cache_path)
    return vector_search(SqlIndex(get_sessionmaker()).search, embedder)


@lru_cache
def get_report_limiter() -> RateLimiter:
    """One limiter for the process, so a client's reports are counted across requests."""
    return RateLimiter(get_settings().reports_per_hour, HOUR_S)


@lru_cache
def get_catalog() -> Catalog:  # pragma: no cover (tests override this)
    """The curated indicators, read once from the catalog directory."""
    return load_catalog(get_settings().catalog_dir)


@lru_cache
def get_tolerances() -> Tolerances:
    """The tolerances verdicts are judged by, read once from `tolerances.yaml`."""
    return load_tolerances()


ReportLimiter = Annotated[RateLimiter, Depends(get_report_limiter)]
Runner = Annotated[CheckRunner, Depends(get_runner)]
Store = Annotated[CheckStore, Depends(get_store)]
Search = Annotated[CatalogSearch, Depends(get_catalog_search)]
CatalogDep = Annotated[Catalog, Depends(get_catalog)]
TolerancesDep = Annotated[Tolerances, Depends(get_tolerances)]
