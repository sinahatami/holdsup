"""What route handlers depend on: the check runner, the check store and the catalog search.

Handlers take these as `Annotated` parameters (`Runner`, `Store`, `Search`) and never build them.
Tests swap the providers with `app.dependency_overrides`; nothing here connects at import.
"""

from typing import Annotated

from fastapi import Depends, Request

from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import SqlIndex
from holdsup.catalog.search import CatalogSearch, vector_search
from holdsup.config import get_settings
from holdsup.db.session import get_sessionmaker
from holdsup.service.runner import CheckRunner
from holdsup.service.store import CheckStore, SqlCheckStore
from holdsup.service.wiring import build_runner


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


Runner = Annotated[CheckRunner, Depends(get_runner)]
Store = Annotated[CheckStore, Depends(get_store)]
Search = Annotated[CatalogSearch, Depends(get_catalog_search)]
