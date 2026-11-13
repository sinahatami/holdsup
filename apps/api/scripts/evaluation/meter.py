"""What a run spends: model calls, tokens and time per step and provider, and source fetches.

The router and the pipeline are not touched. A `MeteredClient` wraps the router's client and
records every call it makes (failed ones too: they count against a provider's budget). The
step a call belongs to comes from the pipeline's own trace events, which the runner feeds to
`Meter.on_event`; claims run one at a time, so the step that last started is the step calling.
"""

import time
from dataclasses import dataclass, field

from holdsup.adapters.base import FetchedSeries, Filters, SeriesAdapter
from holdsup.adapters.cache import CachedFetcher
from holdsup.pipeline.trace import StepEvent
from holdsup.router.client import ChatRequest, ChatResponse, SupportsChat
from holdsup.router.config import ProviderConfig
from holdsup.router.errors import ProviderError, RateLimited

NO_STEP = "none"


@dataclass(frozen=True)
class Call:
    step: str
    provider: str
    model: str
    ok: bool
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None  # the error's class name, e.g. RateLimited
    daily_limit: bool = False  # a 429 saying the provider's quota for the day is spent


@dataclass
class Meter:
    step: str = NO_STEP
    calls: list[Call] = field(default_factory=list)
    series_requests: int = 0  # asked of the cache
    series_fetches: int = 0  # asked of a source (a miss)

    async def on_event(self, event: StepEvent) -> None:
        """The pipeline's `emit`: remember which step is running."""
        if event.event == "step_started":
            self.step = str(event.step)


class MeteredClient:
    """A `SupportsChat` that records each call, then answers (or raises) like `inner`."""

    def __init__(self, inner: SupportsChat, meter: Meter) -> None:
        self._inner = inner
        self._meter = meter

    def has_key(self, provider: ProviderConfig) -> bool:
        return self._inner.has_key(provider)

    async def complete(self, provider: ProviderConfig, request: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        try:
            response = await self._inner.complete(provider, request)
        except ProviderError as exc:
            daily = isinstance(exc, RateLimited) and exc.daily
            self._record(provider, started, ok=False, error=type(exc).__name__, daily_limit=daily)
            raise
        self._record(
            provider,
            started,
            ok=True,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
        return response

    def _record(
        self,
        provider: ProviderConfig,
        started: float,
        *,
        ok: bool,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        error: str | None = None,
        daily_limit: bool = False,
    ) -> None:
        self._meter.calls.append(
            Call(
                step=self._meter.step,
                provider=provider.name,
                model=provider.model,
                ok=ok,
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error=error,
                daily_limit=daily_limit,
            )
        )


class CountingAdapter:
    """A source adapter that counts the requests that reach it: the cache's misses."""

    def __init__(self, inner: SeriesAdapter, meter: Meter) -> None:
        self._inner = inner
        self._meter = meter
        self.source = inner.source

    async def fetch_series(self, dataset: str, filters: Filters) -> FetchedSeries:
        self._meter.series_fetches += 1
        return await self._inner.fetch_series(dataset, filters)


class CountingFetcher:
    """The cached fetcher, counting every request made of it (hits and misses)."""

    def __init__(self, inner: CachedFetcher, meter: Meter) -> None:
        self._inner = inner
        self._meter = meter

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self._meter.series_requests += 1
        return await self._inner.fetch_series(source, dataset, filters)
