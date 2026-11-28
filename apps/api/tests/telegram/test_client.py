"""The Bot API client: what it sends, and that the token never leaves in an error or a log."""

import json
import logging

import httpx
import pytest
import structlog
from pydantic import SecretStr

from holdsup.logs import configure_logging
from holdsup.telegram.client import API, TelegramClient, TelegramError
from tests.telegram.fakes import SECRET, TOKEN, FakeTelegram, update


async def test_send_replies_in_html_with_one_preview_or_none() -> None:
    fake = FakeTelegram()
    client = fake.client()
    first = await client.send(1, "<b>hi</b>", reply_to=7, preview="https://holdsup.example/x")
    second = await client.send(1, "plain")
    assert (first, second) == (101, 102)
    (_, sent), (_, plain) = fake.calls
    assert sent == {
        "chat_id": 1, "text": "<b>hi</b>", "parse_mode": "HTML",
        "link_preview_options": {"url": "https://holdsup.example/x"},
        "reply_parameters": {"message_id": 7, "allow_sending_without_reply": True},
    }  # fmt: skip
    assert plain["link_preview_options"] == {"is_disabled": True}
    assert "reply_parameters" not in plain


async def test_edit_and_the_webhook_calls() -> None:
    fake = FakeTelegram()
    client = fake.client()
    await client.edit(1, 101, "done", preview="https://holdsup.example/x")
    await client.set_webhook("https://api.example/v1/telegram/webhook", SecretStr(SECRET))
    await client.delete_webhook()
    assert await client.webhook_info() == {}  # the fake answers True, not an object
    methods = [m for m, _ in fake.calls]
    assert methods == ["editMessageText", "setWebhook", "deleteWebhook", "getWebhookInfo"]
    hook = fake.calls[1][1]
    assert hook["secret_token"] == SECRET and hook["allowed_updates"] == ["message"]


async def test_updates_are_read_for_polling() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload == {"timeout": 5, "allowed_updates": ["message"], "offset": 3}
        return httpx.Response(200, json={"ok": True, "result": [update("x", update_id=3)]})

    http = httpx.AsyncClient(base_url=API, transport=httpx.MockTransport(answer))
    (got,) = await TelegramClient(SecretStr(TOKEN), http).updates(3, 5)
    assert got.update_id == 3 and got.message is not None and got.message.text == "x"


async def test_an_update_of_an_unknown_shape_is_refused() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": [{"no": "id"}]})

    http = httpx.AsyncClient(base_url=API, transport=httpx.MockTransport(answer))
    with pytest.raises(TelegramError, match="getUpdates"):
        await TelegramClient(SecretStr(TOKEN), http).updates(None, 5)


@pytest.mark.parametrize(
    ("answer", "why"),
    [
        (httpx.Response(400, json={"ok": False, "description": "Bad Request: chat not found"}),
         "chat not found"),
        (httpx.Response(502, text="<html>bad gateway</html>"), "JSONDecodeError"),
        (httpx.Response(500, json=["not", "an", "object"]), "HTTP 500"),
        (httpx.Response(200, json={"ok": True, "result": {"no": "id"}}), "no message_id"),
    ],
)  # fmt: skip
async def test_failures_name_the_method_never_the_token(answer: httpx.Response, why: str) -> None:
    http = httpx.AsyncClient(base_url=API, transport=httpx.MockTransport(lambda _: answer))
    with pytest.raises(TelegramError, match=why) as caught:
        await TelegramClient(SecretStr(TOKEN), http).send(1, "x")
    assert caught.value.method == "sendMessage"
    assert TOKEN not in str(caught.value)
    error = caught.value  # nothing chained that a traceback would print
    assert error.__cause__ is None and (error.__context__ is None or error.__suppress_context__)


async def test_a_network_error_drops_the_address(capsys: pytest.CaptureFixture[str]) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    http = httpx.AsyncClient(base_url=API, transport=httpx.MockTransport(down))
    with pytest.raises(TelegramError, match="ConnectError") as caught:
        await TelegramClient(SecretStr(TOKEN), http).send(1, "x")
    assert TOKEN not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


async def test_no_log_line_holds_the_token(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("DEBUG")
    try:
        await FakeTelegram().client().send(1, "x")  # httpx logs the address at INFO
        logging.getLogger("elsewhere").info("calling %s", f"{API}/bot{TOKEN}/getMe")
        structlog.get_logger("holdsup.test").info("event", url=f"{API}/bot{TOKEN}/getUpdates")
    finally:
        configure_logging("INFO")
    out = capsys.readouterr().out
    assert "HTTP Request: POST" in out and "bot<redacted>/sendMessage" in out
    assert "bot<redacted>/getMe" in out and "bot<redacted>/getUpdates" in out
    assert TOKEN not in out and TOKEN.split(":")[1] not in out
