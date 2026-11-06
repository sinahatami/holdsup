"""Router fault injection: 429 (with/without Retry-After), daily limits, budgets, timeouts,
5xx, malformed JSON, schema-invalid output, exhaustion, and the Gemini live ban."""

from datetime import timedelta

import pytest
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolUnionParam
from pydantic import BaseModel

from holdsup.router import Router, RouterError, Use, load_router_config
from holdsup.router.budgets import InMemoryUsageStore, budget_cap
from holdsup.router.client import ChatRequest, ChatResponse
from holdsup.router.clock import utc_day
from holdsup.router.errors import (
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    RateLimited,
)
from tests.router.fakes import FakeClient, FakeClock, config, provider

MSG: list[ChatCompletionMessageParam] = [
    {"role": "user", "content": "Unemployment in Italy halved since 2015."}
]
TOOLS: list[ChatCompletionToolUnionParam] = [
    {"type": "function", "function": {"name": "search_catalog", "parameters": {}}}
]


class Verdict(BaseModel):
    ok: bool


def make(*providers: dict[str, object], **kw: object) -> tuple[Router, FakeClient, FakeClock]:
    client = FakeClient(**kw)  # type: ignore[arg-type]
    clock = FakeClock()
    return Router(config(*providers), client, clock=clock), client, clock


async def test_uses_first_preference_and_records_call() -> None:
    router, client, _ = make(provider("a"), provider("b"))
    client.script(
        "a", [ChatResponse(content='{"ok": true}', prompt_tokens=11, completion_tokens=3)]
    )

    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)

    assert result.parsed == Verdict(ok=True)
    assert (result.provider, result.model) == ("a", "a-model")
    assert (result.prompt_tokens, result.completion_tokens) == (11, 3)
    assert [(x.provider, x.outcome) for x in result.attempts] == [("a", "ok")]
    assert client.called() == ["a"]


async def test_tokens_are_added_to_daily_usage() -> None:
    store = InMemoryUsageStore()
    client, clock = FakeClient(), FakeClock()
    router = Router(config(provider("a")), client, store, clock)
    client.script("a", [ChatResponse(content="{}", prompt_tokens=11, completion_tokens=3)])
    client.script("a", [ChatResponse(content="{}")])
    await router.complete("extract", MSG, use=Use.LIVE)
    await router.complete("extract", MSG, use=Use.LIVE)
    key = ("a", utc_day(clock.now()))
    assert (store.requests[key], store.tokens[key]) == (2, 14)


async def test_plain_text_call_without_schema() -> None:
    router, client, _ = make(provider("a"))
    client.script("a", [ChatResponse(content="hello")])
    result = await router.complete("extract", MSG, use=Use.LIVE)
    assert result.content == "hello"
    assert result.parsed is None
    assert client.calls[0][1].response_format is None


# --- HTTP 429 ---------------------------------------------------------------------------------


async def test_429_with_retry_after_cools_down_for_that_long() -> None:
    router, client, clock = make(provider("a"), provider("b"))
    client.script("a", [RateLimited(retry_after_s=20)])

    first = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)
    assert first.provider == "b"
    assert [x.outcome for x in first.attempts] == ["rate_limited", "ok"]

    clock.advance(19)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    clock.advance(2)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"
    assert client.called() == ["a", "b", "b", "a"]


async def test_429_without_retry_after_uses_default_cooldown() -> None:
    router, client, clock = make(provider("a"), provider("b"))
    client.script("a", [RateLimited(retry_after_s=None)])

    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    clock.advance(59)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    clock.advance(2)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"


async def test_daily_limit_error_exhausts_provider_until_utc_midnight() -> None:
    router, client, clock = make(provider("a"), provider("b"))
    client.script("a", [RateLimited(retry_after_s=5, daily=True)])

    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    clock.advance(6 * 3600)  # 18:00 UTC, still the same day
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    clock.advance(6 * 3600 + 1)  # just past midnight
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"


# --- budgets ----------------------------------------------------------------------------------


async def test_daily_budget_stops_at_90_percent_without_waiting_for_errors() -> None:
    store = InMemoryUsageStore()
    client, clock = FakeClient(), FakeClock()
    router = Router(config(provider("a", rpd=10), provider("b")), client, store, clock)

    used = [(await router.complete("extract", MSG, use=Use.LIVE)).provider for _ in range(10)]

    assert budget_cap(10) == 9
    assert used == ["a"] * 9 + ["b"]
    assert store.requests[("a", utc_day(clock.now()))] == 9


async def test_daily_budget_resets_on_next_utc_day() -> None:
    store = InMemoryUsageStore()
    client, clock = FakeClient(), FakeClock()
    router = Router(config(provider("a", rpd=2), provider("b")), client, store, clock)
    store.requests[("a", utc_day(clock.now()))] = 1  # persisted from before a restart

    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    clock.advance(timedelta(days=1).total_seconds())
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"


async def test_minute_budget_stops_at_90_percent_and_frees_after_a_minute() -> None:
    router, _, clock = make(provider("a", rpm=10), provider("b"))

    used = [(await router.complete("extract", MSG, use=Use.LIVE)).provider for _ in range(10)]
    assert used == ["a"] * 9 + ["b"]

    clock.advance(60)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"


async def test_remaining_today_reports_budget_left() -> None:
    router, _, clock = make(provider("a", rpd=100), provider("b"))
    await router.complete("extract", MSG, use=Use.LIVE)
    a, b = router.config.providers
    assert await router.budgets.remaining_today(a, clock.now()) == 89
    assert await router.budgets.remaining_today(b, clock.now()) is None


# --- timeouts, 5xx, circuit breaker -----------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "outcome"),
    [
        (ProviderTimeout("read timeout"), "timeout"),
        (ProviderUnavailable("HTTP 503"), "unavailable"),
        (ProviderRejected("HTTP 401"), "rejected"),
    ],
)
async def test_failure_falls_through_to_next_provider(error: Exception, outcome: str) -> None:
    router, client, _ = make(provider("a"), provider("b"))
    client.script("a", [error])  # type: ignore[list-item]

    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)

    assert result.provider == "b"
    assert [x.outcome for x in result.attempts] == [outcome, "ok"]


@pytest.mark.parametrize("error", [ProviderTimeout("timeout"), ProviderUnavailable("HTTP 502")])
async def test_breaker_opens_after_three_failures_and_half_opens_after_60s(
    error: Exception,
) -> None:
    router, client, clock = make(provider("a"), provider("b"))
    client.script("a", [error, error, error, error])  # type: ignore[list-item]

    for _ in range(3):
        assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    assert client.called().count("a") == 3

    # Open: "a" is not even tried.
    await router.complete("extract", MSG, use=Use.LIVE)
    assert client.called().count("a") == 3

    # Half-open after 60 s: one trial call; it fails, so the breaker re-opens.
    clock.advance(60)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    assert client.called().count("a") == 4
    await router.complete("extract", MSG, use=Use.LIVE)
    assert client.called().count("a") == 4

    # Next trial succeeds and closes the breaker.
    clock.advance(60)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"


async def test_success_resets_consecutive_failure_count() -> None:
    router, client, _ = make(provider("a"), provider("b"))
    t = ProviderTimeout("t")
    ok = ChatResponse(content="{}")
    client.script("a", [t, t, ok, t, t])

    for _ in range(5):
        await router.complete("extract", MSG, use=Use.LIVE)
    assert not router.breaker.is_open("a", 0)
    assert client.called().count("a") == 5


# --- malformed and schema-invalid output ------------------------------------------------------


async def test_malformed_json_is_retried_once_with_the_error() -> None:
    router, client, _ = make(provider("a"), provider("b"))
    client.script(
        "a", [ChatResponse(content="Sure! {ok: yes"), ChatResponse(content='{"ok": false}')]
    )

    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)

    assert result.provider == "a"
    assert result.parsed == Verdict(ok=False)
    assert [x.outcome for x in result.attempts] == ["malformed", "ok"]
    retry = client.calls[1][1].messages
    assert retry[-2] == {"role": "assistant", "content": "Sure! {ok: yes"}
    assert retry[-1]["role"] == "user"
    assert "Invalid JSON" in str(retry[-1]["content"])


async def test_schema_invalid_twice_moves_to_next_provider() -> None:
    router, client, _ = make(provider("a"), provider("b"))
    bad = ChatResponse(content='{"ok": "definitely"}')
    client.script("a", [bad, bad])

    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)

    assert result.provider == "b"
    assert [(x.provider, x.outcome) for x in result.attempts] == [
        ("a", "malformed"),
        ("a", "malformed"),
        ("b", "ok"),
    ]


async def test_empty_content_counts_as_malformed() -> None:
    router, client, _ = make(provider("a"), provider("b"))
    client.script("a", [ChatResponse(content=None), ChatResponse(content="")])
    assert (await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)).provider == "b"


async def test_schema_retry_skipped_when_budget_is_spent() -> None:
    router, client, _ = make(provider("a", rpm=2), provider("b"))  # cap: 1 per minute
    client.script("a", [ChatResponse(content="nope")])
    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)
    assert [(x.provider, x.outcome) for x in result.attempts] == [("a", "malformed"), ("b", "ok")]


async def test_json_schema_provider_gets_schema_response_format() -> None:
    router, client, _ = make(provider("a"))
    await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)
    request: ChatRequest = client.calls[0][1]
    assert request.response_format is not None
    assert request.response_format["type"] == "json_schema"
    assert list(request.messages) == MSG


async def test_json_object_provider_gets_schema_in_system_message() -> None:
    router, client, _ = make(provider("a", capabilities=("json_object",)))
    await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)
    request: ChatRequest = client.calls[0][1]
    assert request.response_format == {"type": "json_object"}
    first = request.messages[0]
    assert first["role"] == "system"
    assert '"ok"' in str(first["content"])


# --- eligibility ------------------------------------------------------------------------------


async def test_providers_without_needed_capability_or_key_are_skipped() -> None:
    router, client, _ = make(
        provider("no-tools", capabilities=("json_object",)),
        provider("no-key"),
        provider("c"),
        keys={"no-tools", "c"},
    )
    result = await router.complete("extract", MSG, use=Use.LIVE, tools=TOOLS)
    assert result.provider == "c"
    assert client.called() == ["c"]


async def test_text_only_provider_cannot_serve_schema_calls() -> None:
    router, _, _ = make(provider("a", capabilities=()), provider("b"))
    assert (await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)).provider == "b"
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "a"


async def test_unknown_step_is_an_error() -> None:
    router, _, _ = make(provider("a"))
    with pytest.raises(KeyError):
        await router.complete("nope", MSG, use=Use.LIVE)


# --- exhaustion -------------------------------------------------------------------------------


async def test_all_exhausted_raises_router_error_with_soonest_retry() -> None:
    router, client, _ = make(provider("a"), provider("b"))
    client.script("a", [RateLimited(retry_after_s=30)])
    client.script("b", [RateLimited(retry_after_s=90)])

    with pytest.raises(RouterError) as info:
        await router.complete("extract", MSG, use=Use.LIVE)
    assert info.value.attempts == ["a:rate_limited", "b:rate_limited"]
    assert info.value.retry_after_s == pytest.approx(30)
    assert "retry in ~30s" in str(info.value)

    # Second call: nothing is attempted, still a typed error.
    with pytest.raises(RouterError) as again:
        await router.complete("extract", MSG, use=Use.LIVE)
    assert again.value.attempts == []
    assert again.value.retry_after_s == pytest.approx(30)
    assert len(client.calls) == 2


async def test_no_candidates_at_all_raises_router_error() -> None:
    router, _, _ = make(provider("a"), keys=set())
    with pytest.raises(RouterError) as info:
        await router.complete("extract", MSG, use=Use.LIVE)
    assert info.value.retry_after_s is None
    assert "no provider available" in str(info.value)


# --- Gemini is never live (D003) --------------------------------------------------------------


def gemini() -> dict[str, object]:
    return provider(
        "gemini-flash", use="offline", base_url="https://generativelanguage.googleapis.com/v1beta/"
    )


async def test_offline_provider_is_never_selected_for_live() -> None:
    router, client, _ = make(provider("a"), gemini())
    client.script("a", [RateLimited(retry_after_s=60)])

    with pytest.raises(RouterError):
        await router.complete("extract", MSG, use=Use.LIVE)
    assert "gemini-flash" not in client.called()

    offline = await router.complete("extract", MSG, use=Use.OFFLINE)
    assert offline.provider == "gemini-flash"


async def test_live_providers_also_serve_offline_jobs() -> None:
    router, _, _ = make(provider("a"), gemini())
    assert (await router.complete("extract", MSG, use=Use.OFFLINE)).provider == "a"


def test_config_rejects_gemini_marked_live() -> None:
    with pytest.raises(ValueError, match="offline"):
        config(provider("gemini-pro", use="live"))
    with pytest.raises(ValueError, match="offline"):
        config(
            provider("sneaky", use="live", base_url="https://generativelanguage.googleapis.com/")
        )


def test_shipped_providers_yaml_never_offers_gemini_for_live() -> None:
    cfg = load_router_config()
    router = Router(cfg, FakeClient())
    for step in cfg.steps:
        live = [p.name for p in router.candidates(step, Use.LIVE, set())]
        assert live, step
        assert not any("gemini" in name for name in live), step
    assert any("gemini" in p.name for p in router.candidates("extract", Use.OFFLINE, set()))


def test_config_rejects_unknown_and_duplicate_providers() -> None:
    with pytest.raises(ValueError, match="unknown providers"):
        config(provider("a"), steps={"extract": ["a", "ghost"]})
    with pytest.raises(ValueError, match="unique"):
        config(provider("a"), provider("a"))
    with pytest.raises(KeyError):
        config(provider("a")).provider("ghost")


# --- pacing (min_interval_s) ------------------------------------------------------------------


def paced_router(interval: float) -> tuple[Router, FakeClient, FakeClock, list[float]]:
    p = provider("a")
    p["min_interval_s"] = interval
    client, clock = FakeClient(), FakeClock()
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock.advance(seconds)

    return Router(config(p, provider("b")), client, clock=clock, sleep=sleep), client, clock, slept


async def test_short_pacing_gap_is_waited_out_not_skipped() -> None:
    router, client, clock, slept = paced_router(1.5)
    await router.complete("extract", MSG, use=Use.LIVE)
    clock.advance(0.5)
    await router.complete("extract", MSG, use=Use.LIVE)
    assert client.called() == ["a", "a"]
    assert slept == [pytest.approx(1.0)]


async def test_pacing_applies_to_the_schema_repair_retry() -> None:
    router, client, _, slept = paced_router(1.5)
    client.script("a", [ChatResponse(content="nope"), ChatResponse(content='{"ok": true}')])
    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Verdict)
    assert result.provider == "a"
    assert slept == [pytest.approx(1.5)]


async def test_long_pacing_gap_falls_through_to_next_provider() -> None:
    router, _, _, slept = paced_router(30)
    await router.complete("extract", MSG, use=Use.LIVE)
    assert (await router.complete("extract", MSG, use=Use.LIVE)).provider == "b"
    assert slept == []


async def test_router_error_carries_attempt_details() -> None:
    router, client, _ = make(provider("a"))
    client.script("a", [ProviderRejected("HTTP 404: model gone")])
    with pytest.raises(RouterError) as info:
        await router.complete("extract", MSG, use=Use.LIVE)
    assert info.value.details == ["a rejected: HTTP 404: model gone"]
    assert str(RateLimited(retry_after_s=3, daily=True, message="m")) == (
        "HTTP 429 daily quota, retry-after 3s: m"
    )
