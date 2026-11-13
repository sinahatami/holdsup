"""The meter: model calls by step and provider, and source requests against cache hits."""

from datetime import UTC, datetime

import pytest
from scripts.evaluation.meter import (
    NO_STEP,
    CountingAdapter,
    CountingFetcher,
    Meter,
    MeteredClient,
)

from holdsup.adapters.base import FetchedSeries, Filters, Observation
from holdsup.adapters.cache import CachedFetcher, InMemorySeriesCacheStore
from holdsup.pipeline.trace import Step, StepEvent
from holdsup.router.client import ChatRequest, ChatResponse
from holdsup.router.config import ProviderConfig
from holdsup.router.errors import RateLimited
from tests.router.fakes import FakeClient, provider


def a_provider() -> ProviderConfig:
    return ProviderConfig.model_validate(provider("groq"))


REQUEST = ChatRequest(messages=[{"role": "user", "content": "hi"}])


async def test_a_call_is_recorded_with_the_step_that_was_running() -> None:
    meter = Meter()
    client = FakeClient()
    client.script("groq", [ChatResponse(content="{}", prompt_tokens=7, completion_tokens=3)])
    await meter.on_event(StepEvent(event="step_started", step=Step.MATCH, claim=0))

    response = await MeteredClient(client, meter).complete(a_provider(), REQUEST)

    assert response.content == "{}"
    [call] = meter.calls
    assert (call.step, call.provider, call.model) == ("match", "groq", "groq-model")
    assert (call.ok, call.prompt_tokens, call.completion_tokens, call.error) == (True, 7, 3, None)
    assert call.latency_ms >= 0


async def test_a_failed_call_is_recorded_too_and_still_raises() -> None:
    meter = Meter()
    client = FakeClient()
    client.script("groq", [RateLimited(retry_after_s=2, message="slow down")])

    with pytest.raises(RateLimited):
        await MeteredClient(client, meter).complete(a_provider(), REQUEST)

    [call] = meter.calls
    assert (call.ok, call.error, call.step) == (False, "RateLimited", NO_STEP)
    assert call.daily_limit is False  # a per-minute limit: the provider is back in a moment


async def test_a_spent_daily_quota_is_recorded_as_such() -> None:
    meter = Meter()
    client = FakeClient()
    client.script("groq", [RateLimited(daily=True, message="tokens per day")])

    with pytest.raises(RateLimited):
        await MeteredClient(client, meter).complete(a_provider(), REQUEST)

    [call] = meter.calls
    assert (call.ok, call.error, call.daily_limit) == (False, "RateLimited", True)


async def test_only_a_step_starting_changes_the_step() -> None:
    meter = Meter()
    await meter.on_event(StepEvent(event="step_started", step=Step.PLAN, claim=0))
    await meter.on_event(StepEvent(event="step_done", step=Step.PLAN, claim=0, summary="ok"))

    assert meter.step == "plan"


def test_the_client_has_a_key_when_the_inner_client_does() -> None:
    client = MeteredClient(FakeClient(keys={"groq"}), Meter())

    assert client.has_key(a_provider())
    assert not MeteredClient(FakeClient(keys=set()), Meter()).has_key(a_provider())


class OneSeriesAdapter:
    source = "eurostat"

    async def fetch_series(self, dataset: str, filters: Filters) -> FetchedSeries:
        return FetchedSeries(
            source="eurostat",
            dataset=dataset,
            url="https://example.invalid/x",
            retrieved_at=datetime.now(UTC),
            raw_sha256="ab" * 32,
            observations=[Observation("IT", "2023", 7.7)],
        )


async def test_a_second_request_for_the_same_series_is_a_cache_hit() -> None:
    meter = Meter()
    adapter = CountingAdapter(OneSeriesAdapter(), meter)
    fetcher = CountingFetcher(
        CachedFetcher({"eurostat": adapter}, InMemorySeriesCacheStore()), meter
    )

    await fetcher.fetch_series("eurostat", "une_rt_a", {"geo": "IT"})
    await fetcher.fetch_series("eurostat", "une_rt_a", {"geo": "IT"})
    await fetcher.fetch_series("eurostat", "une_rt_a", {"geo": "FR"})

    assert adapter.source == "eurostat"
    assert (meter.series_requests, meter.series_fetches) == (3, 2)
