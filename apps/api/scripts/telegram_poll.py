"""Run the Telegram bot on this machine by long polling (no public address needed).

Usage (from the repo root): make telegram-poll
Needs a separate development bot (BotFather) whose token is TELEGRAM_BOT_TOKEN in .env, plus
DATABASE_URL and the model keys, like `make dev-api`. Polling fails while the bot has a
webhook, so never point it at the production bot. Every new claim spends the providers'
daily quota: try it with gallery claims (checked before, no model call).
Stops with Ctrl+C.
"""

import asyncio

import httpx

from holdsup.config import get_settings
from holdsup.logs import configure_logging
from holdsup.page import read_page
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.submit import Submitter
from holdsup.service.wiring import HOUR_S, build_runner
from holdsup.telegram.bot import TelegramBot
from holdsup.telegram.client import API, TelegramClient, TelegramError

WAIT_S = 30  # each poll waits this long for a message


async def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.telegram_bot_token is None:
        print("Set TELEGRAM_BOT_TOKEN in .env to a development bot's token (BotFather).")
        return 1
    built = build_runner(settings)
    checks = Submitter(built.runner, read_page, RateLimiter(settings.pages_per_hour, HOUR_S))
    async with httpx.AsyncClient(base_url=API) as http:
        bot = TelegramBot(TelegramClient(settings.telegram_bot_token, http), settings.web_origin)
        offset: int | None = None
        print("Polling; send the bot a message. Ctrl+C stops.")
        try:
            while True:
                try:
                    updates = await bot.client.updates(offset, WAIT_S)
                except TelegramError as exc:
                    print(f"Telegram refused the poll ({exc}). A bot with a webhook cannot poll.")
                    return 1
                for update in updates:
                    offset = update.update_id + 1
                    await bot.handle(update, checks)
        finally:
            await built.close()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(0) from None
