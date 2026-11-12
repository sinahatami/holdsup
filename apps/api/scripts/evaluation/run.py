"""Run benchmark texts through the real pipeline, one at a time, and score each.

One at a time on purpose: the providers are rate-limited, and a model call is attributed to
the step that was running. The ledger (the answer cache) is not used: every text is checked
from scratch, so the figures describe the pipeline, not what happens to be cached.
"""

import time
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from holdsup.adapters.cache import CachedFetcher, InMemorySeriesCacheStore
from holdsup.adapters.registry import build_adapters
from holdsup.catalog.embed import default_embedder
from holdsup.catalog.index import InMemoryIndex
from holdsup.catalog.schema import Catalog
from holdsup.catalog.search import CatalogSearch, vector_search
from holdsup.config import get_settings
from holdsup.pipeline.run import Pipeline
from holdsup.router import Router, RouterConfig, RouterError, Use
from holdsup.router.client import OpenAICompatibleClient
from holdsup.verdict import Tolerances
from scripts.evaluation.benchmark import BenchmarkText
from scripts.evaluation.meter import (
    CountingAdapter,
    CountingFetcher,
    Meter,
    MeteredClient,
)
from scripts.evaluation.score import TOP_K, TextOutcome, not_run, score_text


def only_provider(config: RouterConfig, name: str) -> RouterConfig:
    """The same config with every step served by `name` alone: a per-provider run measures
    that provider's models, with no failing over to a better one. Raises KeyError if the
    provider is unknown."""
    config.provider(name)
    return config.model_copy(update={"steps": {step: (name,) for step in config.steps}})


@dataclass
class Rig:
    """Everything a run needs, built once."""

    pipeline: Pipeline
    search: CatalogSearch
    meter: Meter


@asynccontextmanager
async def live_rig(
    catalog: Catalog, config: RouterConfig, tolerances: Tolerances, use: Use
) -> AsyncIterator[Rig]:  # pragma: no cover (live providers, live sources, the embedding model)
    """The real pipeline: live providers, live sources (cached in memory for the run) and the
    catalog in an in-memory index, so a run needs no database."""
    embedder = default_embedder(get_settings().fastembed_cache_path)
    meter = Meter()
    async with httpx.AsyncClient(timeout=30.0) as http:
        adapters = {
            name: CountingAdapter(adapter, meter) for name, adapter in build_adapters(http).items()
        }
        fetcher = CountingFetcher(CachedFetcher(adapters, InMemorySeriesCacheStore()), meter)
        search = vector_search(InMemoryIndex.build(catalog.indicators, embedder).search, embedder)
        pipeline = Pipeline(
            router=Router(config, MeteredClient(OpenAICompatibleClient(), meter)),
            catalog=catalog,
            search=search,
            fetcher=fetcher,
            tolerances=tolerances,
            use=use,
        )
        yield Rig(pipeline, search, meter)


Progress = Callable[[str], None]


async def evaluate(
    rig: Rig, texts: Sequence[BenchmarkText], progress: Progress = lambda _: None
) -> list[TextOutcome]:
    """Check every text and score it. A text the router cannot serve is recorded as `not_run`;
    any other error is a bug and stops the run."""
    out: list[TextOutcome] = []
    for n, item in enumerate(texts, 1):
        calls_before = len(rig.meter.calls)
        started = time.monotonic()
        try:
            output = await rig.pipeline.run(item.text, rig.meter.on_event)
        except RouterError as exc:
            outcome = not_run(
                item,
                f"router: {exc}",
                round(time.monotonic() - started, 2),
                len(rig.meter.calls) - calls_before,
            )
        else:
            # Retrieval alone, as the matcher's first search sees it: the extracted phrase.
            retrieval = {
                c.index: [h.id for h in await rig.search(c.claim.indicator_phrase, TOP_K)]
                for c in output.claims
            }
            outcome = score_text(
                item,
                output,
                retrieval,
                seconds=round(time.monotonic() - started, 2),
                model_calls=len(rig.meter.calls) - calls_before,
            )
        out.append(outcome)
        progress(_line(n, len(texts), outcome))
    return out


def _line(n: int, total: int, outcome: TextOutcome) -> str:
    if outcome.error is not None:
        return f"[{n}/{total}] {outcome.id}: not run ({outcome.error})"
    right = sum(o.verdict_ok is True for o in outcome.outcomes)
    return (
        f"[{n}/{total}] {outcome.id}: {right}/{outcome.labelled} verdicts right, "
        f"{outcome.model_calls} model calls, {outcome.seconds:.1f}s"
    )
