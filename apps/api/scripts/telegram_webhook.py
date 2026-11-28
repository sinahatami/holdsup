"""Point the Telegram bot at the API's webhook, or show or remove it.

Usage (from the repo root):
    make telegram-webhook ARGS="set https://holdsup-api-<…>.run.app"
    make telegram-webhook ARGS=info
    make telegram-webhook ARGS=delete
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET from the environment; add --ask to type
them instead (hidden), so the production bot's token never goes in .env or the shell history.
The secret must be the one the API on Cloud Run has. `set` drops updates sent while there
was no webhook.
"""

import argparse
import asyncio
import getpass
import re

import httpx
from pydantic import SecretStr

from holdsup.config import TELEGRAM_SECRET, TELEGRAM_TOKEN, get_settings
from holdsup.telegram.client import API, TelegramClient, TelegramError

PATH = "/v1/telegram/webhook"
SHOWN = ("url", "pending_update_count", "last_error_date", "last_error_message", "max_connections")


def secret_from(
    prompt: str, valid: re.Pattern[str], fallback: SecretStr | None, ask: bool
) -> SecretStr:
    if not ask:
        if fallback is None:
            raise SystemExit(f"Not set: {prompt} (or run with --ask).")
        return fallback
    value = getpass.getpass(f"{prompt}: ").strip()  # a paste may end in a line break
    if not valid.fullmatch(value):
        raise SystemExit(f"That does not look like a {prompt}.")
    return SecretStr(value)


async def main(action: str, base: str | None, ask: bool) -> int:
    settings = get_settings()
    token = secret_from("TELEGRAM_BOT_TOKEN", TELEGRAM_TOKEN, settings.telegram_bot_token, ask)
    async with httpx.AsyncClient(base_url=API) as http:
        client = TelegramClient(token, http)
        try:
            if action == "set":
                if not base or not base.startswith("https://"):
                    raise SystemExit("`set` needs the API's https address.")
                secret = secret_from(
                    "TELEGRAM_WEBHOOK_SECRET", TELEGRAM_SECRET,
                    settings.telegram_webhook_secret, ask,
                )  # fmt: skip
                await client.set_webhook(base.rstrip("/") + PATH, secret)
                print("Webhook set.")
            elif action == "delete":
                await client.delete_webhook()
                print("Webhook removed.")
            info = await client.webhook_info()
        except TelegramError as exc:
            print(f"Telegram refused: {exc}")
            return 1
    for key in SHOWN:
        if key in info:
            print(f"{key}: {info[key]}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["set", "info", "delete"])
    parser.add_argument("base", nargs="?", help="the API's address, for `set`")
    parser.add_argument("--ask", action="store_true", help="type the token and secret, hidden")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.action, args.base, args.ask)))
