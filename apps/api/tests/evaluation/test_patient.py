"""PatientRouter: a rate-limited call waits and is retried by itself, the rest of the run is
untouched, and the waits are bounded."""

import pytest
from pydantic import BaseModel
from scripts.evaluation.patient import PatientRouter

from holdsup.router import RouterError, Use
from holdsup.router.errors import RateLimited
from tests.router.fakes import FakeClient, FakeClock, config, provider

MSG = [{"role": "user", "content": "x"}]


class Out(BaseModel):
    ok: bool


def make(
    **kw: float,
) -> tuple[PatientRouter, FakeClient, FakeClock, list[float]]:
    client, clock, waits = FakeClient(), FakeClock(), []

    async def wait(seconds: float) -> None:
        waits.append(seconds)
        clock.advance(seconds)

    router = PatientRouter(config(provider("a")), client, clock=clock, wait=wait, **kw)  # type: ignore[arg-type]
    return router, client, clock, waits


async def test_a_rate_limited_call_waits_and_is_retried() -> None:
    router, client, _, waits = make()
    client.script("a", [RateLimited(retry_after_s=5)])

    result = await router.complete("extract", MSG, use=Use.LIVE, schema=Out)  # type: ignore[arg-type]

    assert result.provider == "a" and client.called() == ["a", "a"]
    assert waits == [6.0]


async def test_a_wait_over_the_cap_is_not_waited_for() -> None:
    router, client, _, waits = make(max_wait_s=90)
    client.script("a", [RateLimited(retry_after_s=3600, daily=True)])

    with pytest.raises(RouterError):
        await router.complete("extract", MSG, use=Use.LIVE, schema=Out)  # type: ignore[arg-type]

    assert waits == [] and client.called() == ["a"]


async def test_the_run_waits_no_longer_than_its_budget() -> None:
    router, client, _, waits = make(budget_s=10)
    client.script("a", [RateLimited(retry_after_s=5)] * 5)

    with pytest.raises(RouterError):
        await router.complete("extract", MSG, use=Use.LIVE, schema=Out)  # type: ignore[arg-type]

    assert waits == [6.0] and router.budget_left_s == 4.0


async def test_a_call_gives_up_after_its_retries() -> None:
    router, client, _, waits = make(call_retries=2)
    client.script("a", [RateLimited(retry_after_s=1)] * 9)

    with pytest.raises(RouterError):
        await router.complete("extract", MSG, use=Use.LIVE, schema=Out)  # type: ignore[arg-type]

    assert len(waits) == 2
