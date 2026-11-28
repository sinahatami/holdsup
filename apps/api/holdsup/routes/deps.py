"""What route handlers depend on: the check runner, the check store, the catalog search, the
page reader and the Telegram bot.

Handlers take these as `Annotated` parameters (`Runner`, `Store`, `Search`, `Pages`) and never
build them.
Tests swap the providers with `app.dependency_overrides`; nothing here connects at import.
"""

from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, Request

from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import SqlIndex
from holdsup.catalog.schema import Catalog, load_catalog
from holdsup.catalog.search import CatalogSearch, vector_search
from holdsup.config import get_settings
from holdsup.db.session import get_sessionmaker
from holdsup.page import PageReader, read_page
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner
from holdsup.service.store import CheckStore, SqlCheckStore
from holdsup.service.wiring import HOUR_S, build_runner
from holdsup.telegram.bot import TelegramBot
from holdsup.telegram.client import API, TelegramClient
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
def get_page_limiter() -> RateLimiter:
    """Links read per client: each is a page fetch, even when its text was checked before."""
    return RateLimiter(get_settings().pages_per_hour, HOUR_S)


def get_page_reader() -> PageReader:  # pragma: no cover (tests override this)
    """Reads a public web page for its paragraphs with figures (the network: never in tests)."""
    return read_page


@lru_cache
def get_catalog() -> Catalog:  # pragma: no cover (tests override this)
    """The curated indicators, read once from the catalog directory."""
    return load_catalog(get_settings().catalog_dir)


@lru_cache
def get_tolerances() -> Tolerances:
    """The tolerances verdicts are judged by, read once from `tolerances.yaml`."""
    return load_tolerances()


def get_telegram_bot(request: Request) -> TelegramBot | None:
    """The app's bot, or None when it is off (no token and webhook secret)."""
    settings = get_settings()
    token, secret = settings.telegram_bot_token, settings.telegram_webhook_secret
    if token is None or secret is None:
        return None
    state = request.app.state
    if getattr(state, "telegram", None) is None:  # pragma: no cover (tests override this)
        client = TelegramClient(token, httpx.AsyncClient(base_url=API))
        state.telegram = TelegramBot(client, settings.web_origin)
    bot: TelegramBot = state.telegram
    return bot


ReportLimiter = Annotated[RateLimiter, Depends(get_report_limiter)]
PageLimiter = Annotated[RateLimiter, Depends(get_page_limiter)]
Pages = Annotated[PageReader, Depends(get_page_reader)]
Runner = Annotated[CheckRunner, Depends(get_runner)]
Store = Annotated[CheckStore, Depends(get_store)]
Search = Annotated[CatalogSearch, Depends(get_catalog_search)]
CatalogDep = Annotated[Catalog, Depends(get_catalog)]
TolerancesDep = Annotated[Tolerances, Depends(get_tolerances)]
