"""POST /v1/telegram/webhook over HTTP: the secret, then each kind of message, with fake
providers, a fake data source, the in-memory store and a fake Bot API."""

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from holdsup.logs import configure_logging
from holdsup.main import create_app
from holdsup.page import PageError, PageExcerpt
from holdsup.routes.deps import get_page_limiter, get_page_reader, get_runner, get_telegram_bot
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner
from holdsup.service.store import InMemoryCheckStore
from holdsup.service.submit import MAX_TEXT, Submitter
from holdsup.telegram import strings
from holdsup.telegram.bot import TelegramBot
from holdsup.telegram.models import Update
from tests.router.fakes import FakeClient
from tests.service.fakes import EXPLANATION, TEXT, happy_script, make_runner
from tests.telegram.fakes import PERSON, SECRET, SITE, TOKEN, FakeTelegram, update

HOOK = "/v1/telegram/webhook"
SIGNED = {"X-Telegram-Bot-Api-Secret-Token": SECRET}
LINK = "https://news.example/jobs"


async def fake_pages(link: str, limit: int) -> PageExcerpt:
    if link != LINK:
        raise PageError("unreadable", "That page did not answer.")
    return PageExcerpt(url=LINK, title="Jobs report", text=TEXT, used=1, found=3)


@dataclass
class Hook:
    http: TestClient
    fake: FakeTelegram
    bot: TelegramBot
    runner: CheckRunner
    models: FakeClient
    store: InMemoryCheckStore

    def post(self, body: dict[str, Any], headers: dict[str, str] = SIGNED) -> int:
        return self.http.post(HOOK, json=body, headers=headers).status_code


@pytest.fixture
def hook(monkeypatch: pytest.MonkeyPatch) -> Iterator[Hook]:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    fake = FakeTelegram()
    bot = TelegramBot(fake.client(), SITE)
    runner, models, store = make_runner(happy_script() * 3, limit=2)
    app = create_app()
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_telegram_bot] = lambda: bot
    app.dependency_overrides[get_page_reader] = lambda: fake_pages
    limiter = RateLimiter(5, 3600.0)
    app.dependency_overrides[get_page_limiter] = lambda: limiter
    with TestClient(app) as http:
        yield Hook(http, fake, bot, runner, models, store)


def test_off_without_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    r = TestClient(create_app()).post(HOOK, json=update(), headers=SIGNED)
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"


def test_off_without_a_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    assert TestClient(create_app()).post(HOOK, json=update(), headers=SIGNED).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"X-Telegram-Bot-Api-Secret-Token": "wrong-secret-0000"}])
def test_a_call_without_the_secret_builds_nothing(hook: Hook, headers: dict[str, str]) -> None:
    built: list[bool] = []

    def runner() -> CheckRunner:
        built.append(True)
        return hook.runner

    hook.http.app.dependency_overrides[get_runner] = runner  # type: ignore[attr-defined]
    assert hook.post(update(TEXT), headers) == 404
    assert built == [] and hook.fake.calls == []


def test_the_webhook_is_not_in_the_api_schema(hook: Hook) -> None:
    assert "/v1/telegram/webhook" not in hook.http.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize(
    ("text", "opening"),
    [("/start", "<b>HoldsUp</b> checks"), ("/help@HoldsUpBot", "Send me a sentence"),
     ("/whatever", "Send me a sentence")],
)  # fmt: skip
def test_commands(hook: Hook, text: str, opening: str) -> None:
    assert hook.post(update(text)) == 204
    ((method, sent),) = hook.fake.calls
    assert method == "sendMessage" and sent["text"].startswith(opening)
    assert f'<a href="{SITE}/privacy">Privacy</a>' in sent["text"]
    assert hook.store.checks == {} and hook.models.calls == []


def test_a_claim_is_checked_and_the_answer_edited_in(hook: Hook) -> None:
    assert hook.post(update(TEXT)) == 204
    (send, checking), (edit, answer) = hook.fake.calls
    assert send == "sendMessage" and checking["text"] == strings.CHECKING
    assert checking["reply_parameters"]["message_id"] == 7
    assert edit == "editMessageText" and answer["message_id"] == hook.fake.next_id
    (stored,) = hook.store.checks.values()
    assert stored.text == TEXT
    receipt = f"{SITE}/check/{stored.id}"
    assert answer["text"].startswith("<b>Holds up</b>")
    assert EXPLANATION in answer["text"] and receipt in answer["text"]
    assert answer["link_preview_options"] == {"url": receipt}


def test_a_claim_checked_before_spends_no_model_call(hook: Hook) -> None:
    hook.post(update(TEXT, update_id=1))
    calls = len(hook.models.calls)
    hook.post(update(TEXT, update_id=2))
    assert len(hook.models.calls) == calls
    answers = [t for m, t in hook.fake.texts() if m == "editMessageText"]
    assert len(answers) == 2 and answers[0].split("\n")[:3] == answers[1].split("\n")[:3]


def test_a_retried_update_is_answered_once(hook: Hook) -> None:
    assert hook.post(update(TEXT, update_id=9)) == 204
    assert hook.post(update(TEXT, update_id=9)) == 204
    assert [m for m, _ in hook.fake.calls] == ["sendMessage", "editMessageText"]
    assert len(hook.store.checks) == 1


async def test_a_retry_while_checking_waits_for_the_same_check() -> None:
    fake = FakeTelegram()
    bot = TelegramBot(fake.client(), SITE)
    runner, _, store = make_runner(happy_script())
    checks = Submitter(runner, fake_pages, RateLimiter(5, 3600.0))
    again = Update.model_validate(update(TEXT, update_id=5))
    await asyncio.gather(bot.handle(again, checks), bot.handle(again, checks))
    assert len(store.checks) == 1
    assert [m for m, _ in fake.calls] == ["sendMessage", "editMessageText"]


def test_each_person_has_their_own_limit(hook: Hook) -> None:
    other = "Spain's unemployment rate fell 3 points between 2015 and 2023."
    third = "France's unemployment rate fell 2 points between 2015 and 2023."
    hook.post(update(TEXT, update_id=1))
    hook.post(update(other, update_id=2))
    hook.post(update(third, update_id=3))  # the third new check this hour: over the limit
    limited = hook.fake.texts()[-1]
    assert limited[0] == "editMessageText"
    assert limited[1].startswith("You have started too many new checks this hour.")
    hook.post(update(third, update_id=4, sender=PERSON + 1))  # someone else is not limited
    assert not hook.fake.texts()[-1][1].startswith("You have started too many")


def test_a_link_is_read_and_its_page_named(hook: Hook) -> None:
    hook.post(update(LINK))
    answer = hook.fake.texts()[-1][1]
    assert answer.startswith(f'From <a href="{LINK}">Jobs report</a>\n\n<b>Holds up</b>')


def test_a_page_that_cannot_be_read_is_said(hook: Hook) -> None:
    hook.post(update("https://down.example/"))
    answer = hook.fake.texts()[-1][1]
    assert answer.startswith("That page did not answer.") and hook.store.checks == {}


def test_a_caption_is_checked_like_text(hook: Hook) -> None:
    hook.post(update(None, caption=TEXT))
    assert len(hook.store.checks) == 1


@pytest.mark.parametrize(
    ("body", "said"),
    [(update(None), strings.NOT_TEXT), (update("   "), strings.NOT_TEXT),
     (update("7" * (MAX_TEXT + 1)), "That is longer than 2,000 characters.")],
)  # fmt: skip
def test_what_is_not_checked(hook: Hook, body: dict[str, Any], said: str) -> None:
    assert hook.post(body) == 204
    ((_, sent),) = hook.fake.calls
    assert sent["text"].startswith(said) and hook.store.checks == {}


@pytest.mark.parametrize(
    "body",
    [update(TEXT, chat_type="group"), update(TEXT, chat_type="channel"),
     update(TEXT, is_bot=True), {"update_id": 3, "edited_message": update(TEXT)["message"]}],
)  # fmt: skip
def test_ignored(hook: Hook, body: dict[str, Any]) -> None:
    assert hook.post(body) == 204
    assert hook.fake.calls == [] and hook.store.checks == {}


@pytest.mark.parametrize("raw", [b"not json", b'{"no": "update_id"}', b"[]"])
def test_an_unreadable_update_is_dropped(hook: Hook, raw: bytes) -> None:
    r = hook.http.post(HOOK, content=raw, headers={**SIGNED, "Content-Type": "application/json"})
    assert r.status_code == 204 and hook.fake.calls == []


def test_a_failed_edit_sends_the_answer_anew(hook: Hook) -> None:
    hook.fake.fail["editMessageText"] = "Bad Request: message to edit not found"
    hook.post(update(TEXT))
    assert [m for m, _ in hook.fake.calls] == ["sendMessage", "editMessageText", "sendMessage"]
    assert hook.fake.calls[-1][1]["text"].startswith("<b>Holds up</b>")


def test_telegram_refusing_every_call_still_answers_204(hook: Hook) -> None:
    hook.fake.fail["sendMessage"] = "Forbidden: bot was blocked by the user"
    assert hook.post(update(TEXT)) == 204
    assert hook.store.checks == {}


def test_an_unexpected_failure_still_answers(hook: Hook, monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken(*_: object, **__: object) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(hook.runner, "submit", broken)
    assert hook.post(update(TEXT)) == 204
    assert hook.fake.texts()[-1] == ("editMessageText", strings.FAILED)


def test_the_bots_logs_name_no_person(hook: Hook, capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    hook.post(update(TEXT, sender=987654321))
    out = capsys.readouterr().out
    assert '"telegram_answered"' in out
    assert "987654321" not in out and TEXT not in out and TOKEN not in out


async def test_a_check_that_fails_says_why() -> None:
    fake = FakeTelegram()
    runner, _, store = make_runner([])  # no provider answers: every one is out of quota
    checks = Submitter(runner, fake_pages, RateLimiter(5, 3600.0))
    await TelegramBot(fake.client(), SITE).handle(Update.model_validate(update(TEXT)), checks)
    method, said = fake.texts()[-1]
    assert method == "editMessageText"
    assert said.startswith("Every free model provider is busy or out of quota.")
    (stored,) = store.checks.values()
    assert stored.error is not None


def test_blank_settings_leave_the_bot_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", " ")
    empty = {"X-Telegram-Bot-Api-Secret-Token": ""}
    assert TestClient(create_app()).post(HOOK, json=update(), headers=empty).status_code == 404
