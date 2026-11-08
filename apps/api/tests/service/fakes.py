"""A whole check with no network and no model: a scripted provider, a fake data source and
the 6-entry test catalog. Shared by the pipeline, runner and API tests."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from holdsup.adapters.base import AdapterError, FetchedSeries, Filters, Observation
from holdsup.catalog.index import InMemoryIndex
from holdsup.catalog.schema import load_catalog
from holdsup.catalog.search import vector_search
from holdsup.pipeline.ledger import Ledger
from holdsup.pipeline.run import Pipeline
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.router.errors import ProviderError
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner
from holdsup.service.store import InMemoryCheckStore
from holdsup.verdict import load_tolerances
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder
from tests.router.fakes import FakeClient, FakeClock, config, provider

CATALOG = load_catalog(FIXTURE_CATALOG)
EMBEDDER = HashEmbedder()
INDEX = InMemoryIndex.build(CATALOG.indicators, EMBEDDER)
TOLERANCES = load_tolerances()
RETRIEVED = datetime(2026, 11, 7, 9, 0, tzinfo=UTC)

TEXT = "Italy's unemployment rate fell 4 points between 2015 and 2023."
QUOTE = "Italy's unemployment rate fell 4 points between 2015 and 2023"
UNEMPLOYMENT_IT = {
    "2015": 11.9, "2016": 11.7, "2017": 11.2, "2018": 10.6, "2019": 9.9,
    "2020": 9.3, "2021": 9.5, "2022": 8.1, "2023": 7.7,
}  # fmt: skip


def claim_json(
    *,
    quote: str = QUOTE,
    geo: str | None = "IT",
    peers: Sequence[str] = (),
    type: str = "percentage_points",
    value: float | None = 4,
    direction: str | None = "down",
) -> dict[str, Any]:
    return {
        "quote": quote,
        "indicator_phrase": "unemployment rate",
        "geo": geo,
        "geo_named": geo is not None,
        "peers": list(peers),
        "start": "2015",
        "start_named": True,
        "end": "2023",
        "lookback": None,
        "office": None,
        "assertion": {
            "type": type,
            "value": value,
            "direction": direction,
            "unit": "points",
            "start_value": None,
            "end_value": None,
        },
    }


def extraction(*claims: dict[str, Any]) -> ChatResponse:
    return reply({"speaker": None, "said_on": None, "claims": list(claims)})


def match_answer(indicator_id: str | None = "unemployment_rate") -> ChatResponse:
    return reply(
        {
            "indicator_id": indicator_id,
            "confidence": "high",
            "reason": "Same measure and unit.",
            "alternatives": ["youth_unemployment_rate"] if indicator_id else [],
        }
    )


def plan_answer(kind: str = "percentage_points", geo: str = "IT") -> ChatResponse:
    call = {"op": "change", "geo": geo, "start": "2015", "end": "2023", "kind": kind}
    return reply({"calls": [call], "answer": [0], "reason": "A change in points answers it."})


EXPLANATION = (
    "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023, a drop of 4.2 "
    "points. That is close to the 4 points claimed."
)


def explain_answer(text: str = EXPLANATION) -> ChatResponse:
    return reply({"explanation": text})


def reply(obj: dict[str, Any]) -> ChatResponse:
    return ChatResponse(content=json.dumps(obj), prompt_tokens=10, completion_tokens=10)


def happy_script() -> list[ChatResponse | ProviderError]:
    """extract → match → plan → explain for TEXT."""
    return [extraction(claim_json()), match_answer(), plan_answer(), explain_answer()]


def observations(values: dict[str, dict[str, float]]) -> list[Observation]:
    return [Observation(geo, p, v) for geo, series in values.items() for p, v in series.items()]


@dataclass
class FakeFetcher:
    rows: list[Observation] = field(default_factory=lambda: observations({"IT": UNEMPLOYMENT_IT}))
    error: AdapterError | None = None
    calls: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls.append((source, dataset, dict(filters)))
        if self.error is not None:
            raise self.error
        return FetchedSeries(
            source=source,
            dataset=dataset,
            url=f"https://example.invalid/{source}/{dataset}",
            retrieved_at=RETRIEVED,
            raw_sha256="ab" * 32,
            observations=self.rows,
            label="Unemployment by sex and age",
        )


STEPS = ("extract", "match", "plan", "explain")


def make_pipeline(
    script: Sequence[ChatResponse | ProviderError], fetcher: FakeFetcher | None = None
) -> tuple[Pipeline, FakeClient, FakeFetcher]:
    client = FakeClient()
    client.script("fake", script)
    router = Router(
        config(provider("fake"), steps={s: ["fake"] for s in STEPS}), client, clock=FakeClock()
    )
    fetcher = fetcher or FakeFetcher()
    pipeline = Pipeline(
        router=router,
        catalog=CATALOG,
        search=vector_search(INDEX.search, EMBEDDER),
        fetcher=fetcher,
        tolerances=TOLERANCES,
        today=lambda: date(2026, 11, 7),
    )
    return pipeline, client, fetcher


def make_runner(
    script: Sequence[ChatResponse | ProviderError],
    *,
    fetcher: FakeFetcher | None = None,
    limit: int = 10,
    store: InMemoryCheckStore | None = None,
) -> tuple[CheckRunner, FakeClient, InMemoryCheckStore]:
    pipeline, client, _ = make_pipeline(script, fetcher)
    store = store if store is not None else InMemoryCheckStore()
    runner = CheckRunner(
        store=store,
        ledger=Ledger(store, EMBEDDER),
        pipeline=pipeline,
        limiter=RateLimiter(limit, 3600.0, clock=FakeClock().now),
    )
    return runner, client, store
