"""Saved model replies: a request asked before is answered from the store, anything else goes
to the provider and is saved; failures are never saved; a whole run replays without a call."""

import re
from pathlib import Path

import pytest
from scripts.evaluation.replay import ReplayClient, ReplayStore, request_key

from holdsup.router.client import ChatRequest, ChatResponse, ToolCall
from holdsup.router.config import ProviderConfig
from holdsup.router.errors import RateLimited
from tests.evaluation.test_cli import benchmark, entry, factory, run
from tests.router.fakes import FakeClient, provider

REQUEST = ChatRequest(messages=[{"role": "user", "content": "Italy's unemployment fell."}])
REPLY = ChatResponse(
    content=None,
    tool_calls=(ToolCall(id="c1", name="search", arguments='{"q": "unemployment"}'),),
    prompt_tokens=12,
    completion_tokens=5,
)


def groq(model: str = "groq-model") -> ProviderConfig:
    return ProviderConfig.model_validate(provider("groq") | {"model": model})


async def test_a_reply_is_saved_then_replayed_without_asking_again(tmp_path: Path) -> None:
    store = ReplayStore(tmp_path)
    client = FakeClient()
    client.script("groq", [REPLY])

    first = await ReplayClient(client, store).complete(groq(), REQUEST)
    again = await ReplayClient(FakeClient(keys=set()), ReplayStore(tmp_path)).complete(
        groq(), REQUEST
    )

    assert first == again == REPLY
    assert len(client.calls) == 1
    assert (store.hits, store.saved) == (0, 1)


@pytest.mark.parametrize(
    ("other_provider", "other_request"),
    [
        (groq(model="another-model"), REQUEST),
        (groq(), ChatRequest(messages=[{"role": "user", "content": "Italy's unemployment rose."}])),
        (groq(), ChatRequest(messages=REQUEST.messages, temperature=0.5)),
    ],
)
def test_another_model_or_request_has_another_key(
    other_provider: ProviderConfig, other_request: ChatRequest
) -> None:
    assert request_key(groq(), REQUEST) == request_key(groq(), REQUEST)
    assert request_key(other_provider, other_request) != request_key(groq(), REQUEST)


async def test_a_failure_is_not_saved_so_the_request_is_asked_again(tmp_path: Path) -> None:
    store = ReplayStore(tmp_path)
    client = FakeClient()
    client.script("groq", [RateLimited(retry_after_s=2, message="slow down"), REPLY])

    with pytest.raises(RateLimited):
        await ReplayClient(client, store).complete(groq(), REQUEST)
    assert await ReplayClient(client, store).complete(groq(), REQUEST) == REPLY

    assert len(client.calls) == 2 and store.saved == 1


async def test_recording_asks_afresh_and_overwrites_the_saved_reply(tmp_path: Path) -> None:
    store = ReplayStore(tmp_path)
    newer = ChatResponse(content='{"ok": true}')
    client = FakeClient()
    client.script("groq", [REPLY, newer])

    await ReplayClient(client, store, replay=False).complete(groq(), REQUEST)
    await ReplayClient(client, store, replay=False).complete(groq(), REQUEST)

    assert len(client.calls) == 2
    assert await ReplayClient(FakeClient(), ReplayStore(tmp_path)).complete(groq(), REQUEST) == (
        newer
    )


async def test_a_damaged_file_is_asked_again(tmp_path: Path) -> None:
    (tmp_path / f"{request_key(groq(), REQUEST)}.json").write_text("{not json", encoding="utf-8")
    client = FakeClient()
    client.script("groq", [REPLY])

    assert await ReplayClient(client, ReplayStore(tmp_path)).complete(groq(), REQUEST) == REPLY
    assert len(client.calls) == 1


async def test_prune_keeps_only_the_replies_this_run_used(tmp_path: Path) -> None:
    (tmp_path / "old.json").write_text("{}", encoding="utf-8")
    store = ReplayStore(tmp_path)
    client = FakeClient()
    client.script("groq", [REPLY])
    await ReplayClient(client, store).complete(groq(), REQUEST)

    assert store.prune() == 1
    assert [p.stem for p in tmp_path.glob("*.json")] == [request_key(groq(), REQUEST)]
    assert ReplayStore(tmp_path / "missing").prune() == 0


def test_a_recorded_run_replays_with_no_provider_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry())
    replies = tmp_path / "replies"

    assert run(tmp_path, claims, "--record", str(replies)) == 0
    recorded = capsys.readouterr().out
    # No script at all: every request must come from the saved replies to judge the claim.
    assert run(tmp_path, claims, "--replay", str(replies), fake=factory(texts=0)) == 0
    replayed = capsys.readouterr().out

    assert "verdict accuracy 100%" in recorded and "verdict accuracy 100%" in replayed
    saved = re.search(r"model replies: 0 replayed, (\d+) asked and saved", recorded)
    again = re.search(r"model replies: (\d+) replayed, 0 asked and saved, 0 unused", replayed)
    assert saved and again and int(saved[1]) == int(again[1]) > 0


def test_replay_and_record_together_are_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        run(tmp_path, benchmark(tmp_path, entry()), "--replay", "a", "--record", "b")
