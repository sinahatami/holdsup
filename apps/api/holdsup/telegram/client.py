"""The Bot API calls the bot makes, over httpx (no Telegram library: D044).

Every Bot API address holds the token (`/bot<token>/<method>`), so nothing here lets an
address reach a log or an exception: a failed call raises TelegramError with the method name
and Telegram's own description only, chained `from None`. httpx's own request log line is
redacted by `holdsup.logs`.
"""

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr, ValidationError

from holdsup.jsontypes import JsonObject
from holdsup.telegram.models import Update

API = "https://api.telegram.org"
TIMEOUT_S = 10.0
NO_PREVIEW: JsonObject = {"is_disabled": True}


class TelegramError(Exception):
    """A Bot API call that failed; the message never holds the token."""

    def __init__(self, method: str, why: str) -> None:
        super().__init__(f"{method}: {why}")
        self.method = method


@dataclass(frozen=True)
class TelegramClient:
    token: SecretStr
    http: httpx.AsyncClient  # base_url=API in production; a mock transport in tests

    # Any: each method's result has its own shape (a Message, True, a list of Updates); the
    # callers below read it through that shape.
    async def call(self, method: str, payload: JsonObject, timeout: float = TIMEOUT_S) -> Any:
        path = f"/bot{self.token.get_secret_value()}/{method}"
        try:
            response = await self.http.post(path, json=payload, timeout=timeout)
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TelegramError(method, type(exc).__name__) from None
        if not isinstance(body, dict) or body.get("ok") is not True:
            why = body.get("description") if isinstance(body, dict) else None
            raise TelegramError(method, str(why or f"HTTP {response.status_code}"))
        return body.get("result")

    async def send(
        self, chat_id: int, html: str, *, reply_to: int | None = None, preview: str | None = None
    ) -> int:
        """Send `html` to the chat; returns the new message's id. `preview` is the one link
        Telegram may draw a preview of (none when None)."""
        payload: JsonObject = {
            "chat_id": chat_id,
            "text": html,
            "parse_mode": "HTML",
            "link_preview_options": {"url": preview} if preview else NO_PREVIEW,
        }
        if reply_to is not None:
            payload["reply_parameters"] = {
                "message_id": reply_to,
                "allow_sending_without_reply": True,
            }
        result = await self.call("sendMessage", payload)
        try:
            return int(result["message_id"])
        except (TypeError, KeyError, ValueError):
            raise TelegramError("sendMessage", "no message_id in the reply") from None

    async def edit(
        self, chat_id: int, message_id: int, html: str, *, preview: str | None = None
    ) -> None:
        await self.call(
            "editMessageText",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": html,
                "parse_mode": "HTML",
                "link_preview_options": {"url": preview} if preview else NO_PREVIEW,
            },
        )

    async def set_webhook(self, url: str, secret: SecretStr) -> None:
        await self.call(
            "setWebhook",
            {
                "url": url,
                "secret_token": secret.get_secret_value(),
                "allowed_updates": ["message"],
                "drop_pending_updates": True,
            },
        )

    async def delete_webhook(self) -> None:
        await self.call("deleteWebhook", {"drop_pending_updates": False})

    async def webhook_info(self) -> JsonObject:
        info = await self.call("getWebhookInfo", {})
        return info if isinstance(info, dict) else {}

    async def updates(self, offset: int | None, wait_s: int) -> list[Update]:
        """Long polling, for local development only (it fails while a webhook is set)."""
        payload: JsonObject = {"timeout": wait_s, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        result = await self.call("getUpdates", payload, timeout=wait_s + TIMEOUT_S)
        try:
            return [Update.model_validate(u) for u in result or []]
        except (TypeError, ValidationError):
            raise TelegramError("getUpdates", "an update of an unknown shape") from None
