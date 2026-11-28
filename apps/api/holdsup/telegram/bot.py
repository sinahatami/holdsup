"""The bot: one Telegram update in, one answer out.

A message in a private chat is checked like pasted text: the bot answers "Checking…", follows
the check's events to its result, and edits that answer into the verdict. `/start` and `/help`
explain it. Groups, channels, edits and other bots are ignored.

Cloud Run gives the API CPU only while a request is open (request-based billing), so the
webhook holds Telegram's request until the answer is sent. If Telegram gives up and sends the
same update again, the retry waits on the work already running rather than starting a second
check. The person's Telegram id is the key their limits count, in memory only: it is never
stored or logged.
"""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from uuid import UUID

import structlog

from holdsup.problems import Problem, ProblemError, internal_error, interrupted
from holdsup.service.runner import CheckRunner
from holdsup.service.store import CheckResult
from holdsup.service.submit import MAX_TEXT, Submitter
from holdsup.telegram import strings
from holdsup.telegram.client import TelegramClient, TelegramError
from holdsup.telegram.format import attr, problem_message, receipt_url, result_message, text
from holdsup.telegram.models import Message, Update

log = structlog.get_logger(__name__)

REMEMBER = 1_000  # update ids kept to recognise Telegram's retries

Outcome = CheckResult | Problem


async def outcome(runner: CheckRunner, check_id: UUID) -> Outcome:
    """The check's result or its problem, waiting for it while it runs."""
    async for event in runner.events(check_id):
        if event.name == "result":
            return CheckResult.model_validate(event.data)
        if event.name == "error":
            return Problem.model_validate(event.data)
    return interrupted()


@dataclass
class TelegramBot:
    client: TelegramClient
    site: str  # the web app's origin, for receipt links
    _seen: OrderedDict[int, asyncio.Task[None]] = field(default_factory=OrderedDict)

    async def handle(self, update: Update, checks: Submitter) -> None:
        """Answer `update` once, however often Telegram sends it. Never raises."""
        task = self._seen.get(update.update_id)
        if task is None:
            task = asyncio.create_task(self._answer(update, checks))
            self._seen[update.update_id] = task
            while len(self._seen) > REMEMBER:
                self._seen.popitem(last=False)
        else:
            log.info("telegram_retry")
        # Shielded: a dropped connection must not cancel a check someone is waiting for.
        await asyncio.shield(task)

    async def _answer(self, update: Update, checks: Submitter) -> None:
        message = update.message
        try:
            if message is None or not _personal(message):
                log.info("telegram_ignored", kind="other" if message is None else message.chat.type)
                return
            await self._reply(message, checks)
        except TelegramError as exc:
            log.warning("telegram_call_failed", method=exc.method, error=str(exc))
        except Exception:
            log.exception("telegram_update_failed")

    async def _reply(self, message: Message, checks: Submitter) -> None:
        chat = message.chat.id
        words = (message.text or message.caption or "").strip()
        site = attr(self.site)
        if not words:
            await self.client.send(chat, strings.NOT_TEXT)
            log.info("telegram_answered", kind="not_text")
            return
        if words.startswith("/"):
            command = words.split(maxsplit=1)[0].split("@", 1)[0].lower()
            template = strings.START if command == "/start" else strings.HELP
            await self.client.send(chat, template.format(site=site, example=text(strings.EXAMPLE)))
            log.info("telegram_answered", kind="command")
            return
        if len(words) > MAX_TEXT:
            await self.client.send(chat, strings.TOO_LONG.format(limit=f"{MAX_TEXT:,}"))
            log.info("telegram_answered", kind="too_long")
            return
        placeholder = await self.client.send(chat, strings.CHECKING, reply_to=message.message_id)
        assert message.sender is not None  # noqa: S101 (_personal checked it)
        result = await self._check(words, f"telegram:{message.sender.id}", checks)
        if isinstance(result, CheckResult):
            html = result_message(result, self.site)
            preview = receipt_url(self.site, result) if result.claims else None
            kind = "cached" if result.cached_from else "checked"
        else:
            html, preview, kind = problem_message(result), None, result.type
        await self._show(chat, placeholder, html, preview)
        log.info("telegram_answered", kind=kind)

    @staticmethod
    async def _check(words: str, key: str, checks: Submitter) -> Outcome:
        """The check's outcome; never raises, so "Checking…" always becomes an answer."""
        try:
            submitted = await checks.submit(words, key)
            return await outcome(checks.runner, submitted.id)
        except ProblemError as exc:
            return exc.problem
        except Exception:
            log.exception("telegram_check_lost")
            return internal_error()

    async def _show(self, chat: int, placeholder: int, html: str, preview: str | None) -> None:
        """Edit "Checking…" into the answer; if that fails (it was deleted), send it anew."""
        try:
            await self.client.edit(chat, placeholder, html, preview=preview)
        except TelegramError as exc:
            log.warning("telegram_edit_failed", error=str(exc))
            await self.client.send(chat, html, preview=preview)


def _personal(message: Message) -> bool:
    """A person writing to the bot in a private chat (not a group, a channel or a bot)."""
    sender = message.sender
    return message.chat.type == "private" and sender is not None and not sender.is_bot
