"""What /status says about each provider (P3.7): the router's own state, read without a call."""

from openai.types.chat import ChatCompletionMessageParam

from holdsup.router import ProviderState, ProviderStatus, Router, Use
from holdsup.router.budgets import budget_cap
from holdsup.router.errors import ProviderUnavailable, RateLimited
from tests.router.fakes import FakeClient, FakeClock, config, provider

MSG: list[ChatCompletionMessageParam] = [{"role": "user", "content": "A claim."}]
STEPS = {"extract": ["a", "b"], "match": ["b"], "plan": ["a", "b"]}


def make(keys: set[str] | None = None) -> tuple[Router, FakeClient, FakeClock]:
    client, clock = FakeClient(keys=keys), FakeClock()
    providers = (provider("a", rpd=100), provider("b"), provider("g", use="offline"))
    return Router(config(*providers, steps=STEPS), client, clock=clock), client, clock


def states(statuses: list[ProviderStatus]) -> dict[str, tuple[ProviderState, float]]:
    return {s.name: (s.state, s.wait_s) for s in statuses}


async def test_live_providers_with_their_steps_and_daily_budget() -> None:
    router, _, _ = make()
    a, b = await router.status()  # the offline-only provider is not listed
    assert (a.name, a.label, a.model, a.state, a.wait_s) == (
        "a", "a-model", "a-model", ProviderState.READY, 0.0,
    )  # fmt: skip
    assert a.steps == ["extract", "plan"] and b.steps == ["extract", "match", "plan"]
    assert (a.daily_cap, a.remaining_today) == (budget_cap(100), 90)
    assert (b.daily_cap, b.remaining_today) == (None, None)  # no daily limit

    await router.complete("extract", MSG, use=Use.LIVE)
    [a, _] = await router.status()
    assert a.remaining_today == 89  # attempts count, as providers count them


async def test_a_429_cools_a_provider_down_for_as_long_as_it_asked() -> None:
    router, client, clock = make()
    client.script("a", [RateLimited(retry_after_s=20)])
    await router.complete("extract", MSG, use=Use.LIVE)
    clock.advance(5)
    assert states(await router.status())["a"] == (ProviderState.COOLING_DOWN, 15.0)
    clock.advance(16)
    assert states(await router.status())["a"] == (ProviderState.READY, 0.0)


async def test_failing_calls_open_the_breaker() -> None:
    router, client, _ = make()
    client.script("a", [ProviderUnavailable("down")] * 3)
    for _ in range(3):
        await router.complete("extract", MSG, use=Use.LIVE)
    state, wait = states(await router.status())["a"]
    assert state is ProviderState.FAILING and wait > 0


async def test_a_spent_day_waits_for_midnight_utc() -> None:
    router, client, _ = make()
    client.script("a", [RateLimited(retry_after_s=None, daily=True)])
    await router.complete("extract", MSG, use=Use.LIVE)
    state, wait = states(await router.status())["a"]
    assert state is ProviderState.OUT_OF_BUDGET and 0 < wait <= 24 * 3600


async def test_the_daily_cap_reached_is_out_of_budget() -> None:
    router, _, _ = make()
    for _ in range(budget_cap(100)):
        await router.complete("plan", MSG, use=Use.LIVE)
    [a, _] = await router.status()
    assert (a.state, a.remaining_today) == (ProviderState.OUT_OF_BUDGET, 0)


async def test_a_provider_without_a_key_is_not_configured() -> None:
    router, _, _ = make(keys={"b"})
    assert states(await router.status())["a"] == (ProviderState.NOT_CONFIGURED, 0.0)
