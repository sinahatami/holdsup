"""Background runs, event channels, the ledger and the limit, with the in-memory store."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from holdsup.adapters.base import SourceUnavailable
from holdsup.problems import ProblemError
from holdsup.router.errors import ProviderUnavailable
from holdsup.service.runner import Channel, CheckRunner, Event
from holdsup.service.store import CheckResult, CheckStatus, StoredCheck
from tests.service.fakes import (
    TEXT,
    FakeFetcher,
    claim_json,
    extraction,
    happy_script,
    make_runner,
    match_answer,
)


async def drain(runner: CheckRunner, check_id: object, after: int = -1) -> list[Event]:
    assert isinstance(check_id, type(uuid4()))
    return [e async for e in runner.events(check_id, after)]


async def finish(runner: CheckRunner) -> None:
    await asyncio.gather(*runner.tasks)


async def test_a_new_check_runs_in_the_background_and_is_stored() -> None:
    runner, client, store = make_runner(happy_script())
    submitted = await runner.submit(TEXT, "1.1.1.1")
    assert submitted.status is CheckStatus.QUEUED and not submitted.cached
    events = await drain(runner, submitted.id)

    names = [e.name for e in events]
    assert names[:2] == ["step_started", "step_done"] and events[1].data["step"] == "ledger"
    assert names[-1] == "result" and names.count("result") == 1
    assert [e.index for e in events] == list(range(len(events)))
    assert len(client.calls) == 4

    stored = await store.get(submitted.id)
    assert stored is not None and stored.status is CheckStatus.DONE
    assert stored.result == events[-1].data
    result = CheckResult.model_validate(stored.result)
    assert result.id == submitted.id and result.text == TEXT
    assert result.providers() == ["fake"]
    assert submitted.id in store.ledger  # reusable


async def test_a_repeated_claim_is_answered_from_the_ledger_with_no_model_call() -> None:
    runner, client, store = make_runner(happy_script())
    first = await runner.submit(TEXT, "1.1.1.1")
    await finish(runner)
    calls = len(client.calls)

    again = await runner.submit(
        "  italy's UNEMPLOYMENT rate fell 4 points between 2015 and 2023. ", "2.2.2.2"
    )
    assert again.cached and again.status is CheckStatus.DONE and again.id != first.id
    assert len(client.calls) == calls  # zero model calls
    events = await drain(runner, again.id)
    assert [e.name for e in events] == ["step_started", "step_done", "result"]
    assert events[1].data["summary"].startswith("Checked before on ")
    result = CheckResult.model_validate(events[-1].data)
    assert result.id == again.id and result.cached_from == first.id
    stored = await store.get(again.id)
    assert stored is not None and stored.cached_from == first.id
    assert again.id not in store.ledger  # copies are not ledger entries

    # A copy of a copy still points at the original.
    third = await runner.submit(TEXT, "3.3.3.3")
    third_result = CheckResult.model_validate((await drain(runner, third.id))[-1].data)
    assert third_result.cached_from == first.id


async def test_a_result_with_a_source_down_is_not_reused() -> None:
    script = [extraction(claim_json()), match_answer()]
    runner, _, store = make_runner(script, fetcher=FakeFetcher(error=SourceUnavailable("503")))
    first = await runner.submit(TEXT, "1.1.1.1")
    await finish(runner)
    assert first.id not in store.ledger
    assert (await runner.submit(TEXT, "1.1.1.1")).cached is False


async def test_new_checks_are_limited_per_address_but_cache_hits_are_not() -> None:
    runner, _, _ = make_runner(happy_script(), limit=1)
    await runner.submit(TEXT, "1.1.1.1")
    await finish(runner)
    with pytest.raises(ProblemError) as caught:
        await runner.submit("Germany's unemployment rate fell 1 point.", "1.1.1.1")
    assert caught.value.problem.status == 429 and caught.value.problem.retry_after == 3600
    # The same claim again is a ledger hit: allowed.
    assert (await runner.submit(TEXT, "1.1.1.1")).cached


async def test_out_of_providers_is_an_at_capacity_error() -> None:
    runner, _, store = make_runner([ProviderUnavailable("down")])
    submitted = await runner.submit(TEXT, "1.1.1.1")
    events = await drain(runner, submitted.id)
    assert events[-1].name == "error"
    assert events[-1].data["type"] == "/problems/at-capacity"
    stored = await store.get(submitted.id)
    assert stored is not None and stored.status is CheckStatus.FAILED
    assert stored.error == events[-1].data
    assert submitted.id not in store.ledger


async def test_an_unexpected_failure_is_an_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    runner, _, store = make_runner(happy_script())

    async def boom(*args: object) -> None:
        raise RuntimeError("bug")

    monkeypatch.setattr(store, "finish", boom)
    submitted = await runner.submit(TEXT, "1.1.1.1")
    events = await drain(runner, submitted.id)
    assert events[-1].name == "error" and events[-1].data["status"] == 500


async def test_a_store_failure_while_failing_still_ends_the_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, store = make_runner([ProviderUnavailable("down")])

    async def boom(*args: object) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(store, "fail", boom)
    submitted = await runner.submit(TEXT, "1.1.1.1")
    assert (await drain(runner, submitted.id))[-1].name == "error"


async def test_last_event_id_resumes_after_it() -> None:
    runner, _, _ = make_runner(happy_script())
    submitted = await runner.submit(TEXT, "1.1.1.1")
    everything = await drain(runner, submitted.id)
    rest = await drain(runner, submitted.id, after=3)
    assert rest == everything[4:]


async def test_after_a_restart_the_stream_is_rebuilt_from_the_store() -> None:
    runner, _, store = make_runner(happy_script())
    submitted = await runner.submit(TEXT, "1.1.1.1")
    events = await drain(runner, submitted.id)
    runner.channels.clear()  # what a restart loses

    rebuilt = await drain(runner, submitted.id)
    assert [(e.index, e.name) for e in rebuilt] == [(0, "result")]
    assert rebuilt[0].data == events[-1].data
    # Reconnecting after the last event still ends with the final event.
    assert [e.index for e in await drain(runner, submitted.id, after=7)] == [8]

    failed_id, dead_id = uuid4(), uuid4()
    now = runner.now()
    await store.create(StoredCheck(failed_id, "x", CheckStatus.FAILED, now, error={"status": 503}))
    await store.create(StoredCheck(dead_id, "x", CheckStatus.RUNNING, now))
    assert (await drain(runner, failed_id))[0].data == {"status": 503}
    interrupted = (await drain(runner, dead_id))[0]
    assert interrupted.name == "error" and interrupted.data["type"] == "/problems/interrupted"
    assert await drain(runner, uuid4()) == []


async def test_exists() -> None:
    runner, _, _ = make_runner(happy_script())
    submitted = await runner.submit(TEXT, "1.1.1.1")
    assert await runner.exists(submitted.id)
    runner.channels.clear()
    assert await runner.exists(submitted.id)  # from the store
    assert not await runner.exists(uuid4())


async def test_channels_are_dropped_after_a_while() -> None:
    runner, _, _ = make_runner(happy_script())
    runner.keep_channel_s = 0.01
    submitted = await runner.submit(TEXT, "1.1.1.1")
    await finish(runner)
    await asyncio.sleep(0.05)
    assert submitted.id not in runner.channels


async def test_shutdown_cancels_running_checks() -> None:
    runner, _, store = make_runner(happy_script())
    gate = asyncio.Event()

    async def stuck(text: str, emit: object) -> None:
        await gate.wait()

    runner.pipeline.run = stuck  # type: ignore[method-assign,assignment]
    submitted = await runner.submit(TEXT, "1.1.1.1")
    await asyncio.sleep(0)
    await runner.shutdown()
    stored = await store.get(submitted.id)
    assert stored is not None and stored.status is CheckStatus.RUNNING  # → "interrupted" later
    assert not runner.tasks


async def test_a_follower_waits_for_new_events() -> None:
    channel = Channel()
    seen: list[str] = []

    async def follow() -> None:
        async for event in channel.follow():
            seen.append(event.name)

    task = asyncio.create_task(follow())
    await asyncio.sleep(0)
    await channel.publish("step_started", {})
    await asyncio.sleep(0)
    assert seen == ["step_started"]
    await channel.publish("result", {})
    await channel.close()
    await asyncio.wait_for(task, 1)
    assert seen == ["step_started", "result"]


async def test_ledger_entries_older_than_the_limit_are_ignored() -> None:
    runner, _, _ = make_runner(happy_script() + happy_script())
    await runner.submit(TEXT, "1.1.1.1")
    await finish(runner)
    later = runner.now() + timedelta(days=8)
    runner.ledger.now = lambda: later
    assert (await runner.submit(TEXT, "1.1.1.1")).cached is False
