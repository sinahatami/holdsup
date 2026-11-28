"""A Bot API that records every call (httpx.MockTransport: no network), and updates as
Telegram sends them."""

import json
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import SecretStr

from holdsup.telegram.client import API, TelegramClient

# Made up, and not a real token's shape (those start "AA" after the colon).
TOKEN = "123456:fake-token-for-tests-only_0123456789"  # noqa: S105 (a test value)
SECRET = "test-webhook-secret-0123456789"  # noqa: S105 (a test value)
SITE = "https://holdsup.example"
PERSON = 4242


@dataclass
class FakeTelegram:
    """Answers like the Bot API; `fail` maps a method to the description it fails with."""

    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    fail: dict[str, str] = field(default_factory=dict)
    next_id: int = 100

    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        payload = json.loads(request.content or b"{}")
        self.calls.append((method, payload))
        if method in self.fail:
            return httpx.Response(400, json={"ok": False, "description": self.fail[method]})
        if method == "sendMessage":
            self.next_id += 1
            return httpx.Response(200, json={"ok": True, "result": {"message_id": self.next_id}})
        return httpx.Response(200, json={"ok": True, "result": True})

    def client(self) -> TelegramClient:
        http = httpx.AsyncClient(base_url=API, transport=httpx.MockTransport(self.handler))
        return TelegramClient(SecretStr(TOKEN), http)

    def texts(self) -> list[tuple[str, str]]:
        """(method, text) of every message sent or edited, in order."""
        return [(m, p["text"]) for m, p in self.calls if "text" in p]


def update(
    text: str | None = "hello",
    *,
    update_id: int = 1,
    chat_type: str = "private",
    sender: int = PERSON,
    is_bot: bool = False,
    caption: str | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": 7,
        "date": 1_764_300_000,
        "chat": {"id": sender if chat_type == "private" else -100, "type": chat_type},
        "from": {"id": sender, "is_bot": is_bot, "first_name": "Ada"},
    }
    if text is not None:
        message["text"] = text
    if caption is not None:
        message["caption"] = caption
    return {"update_id": update_id, "message": message}
