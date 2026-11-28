"""The Telegram bot's webhook: Telegram posts each update here (setWebhook, D044).

Off (404) unless the bot's token and webhook secret are set. The secret Telegram sends in a
header is checked before anything else is built, so a stranger's call costs nothing. Left out
of the OpenAPI schema: it is Telegram's, not the web app's.
"""

import hmac
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import ValidationError

from holdsup.config import get_settings
from holdsup.problems import ProblemError, not_found
from holdsup.routes.deps import PageLimiter, Pages, Runner, get_telegram_bot
from holdsup.service.submit import Submitter
from holdsup.telegram.bot import TelegramBot
from holdsup.telegram.models import Update

log = structlog.get_logger(__name__)

router = APIRouter(tags=["telegram"], include_in_schema=False)


def _bot(
    bot: Annotated[TelegramBot | None, Depends(get_telegram_bot)],
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> TelegramBot:
    """The bot, if the call carries its webhook secret; else 404, as if there were none."""
    secret = get_settings().telegram_webhook_secret
    given = x_telegram_bot_api_secret_token
    if bot is None or secret is None or given is None:
        raise ProblemError(not_found("No such page."))
    if not hmac.compare_digest(given.encode(), secret.get_secret_value().encode()):
        log.warning("telegram_wrong_secret")
        raise ProblemError(not_found("No such page."))
    return bot


@router.post("/telegram/webhook", status_code=204)
async def telegram_webhook(
    # First, so a call without the secret is refused before the runner (and its models) load.
    bot: Annotated[TelegramBot, Depends(_bot)],
    request: Request,
    runner: Runner,
    pages: Pages,
    page_limiter: PageLimiter,
) -> Response:
    """Answers once the reply is sent (the open request keeps Cloud Run's CPU on). An update
    the bot cannot read is dropped with a 204, so Telegram does not send it again."""
    try:
        update = Update.model_validate_json(await request.body())
    except ValidationError:
        log.warning("telegram_unreadable_update")
        return Response(status_code=204)
    await bot.handle(update, Submitter(runner, pages, page_limiter))
    return Response(status_code=204)
