"""Runs checks as in-process tasks and streams their events.

`submit` answers at once: a ledger hit is stored as a finished copy (no model call, no rate
limit); anything else is counted against the caller's limit, stored as queued and run in the
background. Each check has a channel holding every event so far, so a stream opened late, or
reopened with Last-Event-ID, replays what it missed. After a restart the channel is gone and
the stream is rebuilt from the stored result.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from typing import Any, Literal
from uuid import UUID, uuid4

import structlog

from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.ledger import Ledger
from holdsup.pipeline.result import Suggestion
from holdsup.pipeline.run import Choice, Pipeline
from holdsup.pipeline.trace import Step, StepEvent
from holdsup.problems import (
    Problem,
    ProblemError,
    at_capacity,
    internal_error,
    interrupted,
    rate_limited,
)
from holdsup.router import RouterError
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.store import CheckResult, CheckStatus, CheckStore, RecheckOf, StoredCheck

log = structlog.get_logger(__name__)

EventName = Literal["step_started", "step_done", "result", "error"]
KEEP_CHANNEL_S = 600.0  # a finished check's events stay in memory this long


@dataclass(frozen=True)
class Event:
    index: int  # the SSE id; Last-Event-ID resumes after it
    name: EventName
    data: dict[str, Any]


@dataclass
class Channel:
    events: list[Event] = field(default_factory=list)
    closed: bool = False
    _changed: asyncio.Condition = field(default_factory=asyncio.Condition)

    async def publish(self, name: EventName, data: dict[str, Any]) -> None:
        async with self._changed:
            self.events.append(Event(len(self.events), name, data))
            self._changed.notify_all()

    async def close(self) -> None:
        async with self._changed:
            self.closed = True
            self._changed.notify_all()

    def _ready(self, i: int) -> bool:
        return i < len(self.events) or self.closed

    async def follow(self, after: int = -1) -> AsyncIterator[Event]:
        """Every event with an index above `after`, waiting for new ones until closed."""
        i = after + 1
        while True:
            async with self._changed:
                await self._changed.wait_for(partial(self._ready, i))
                pending = self.events[i:]
                closed = self.closed
            for event in pending:
                yield event
            i += len(pending)
            if closed and i >= len(self.events):
                return


@dataclass(frozen=True)
class Recheck:
    """What a re-check runs: the claim as first read, the reader's statistic, and the link back."""

    claim: ClaimSpec
    choice: Choice
    of: RecheckOf


@dataclass(frozen=True)
class Submitted:
    id: UUID
    status: CheckStatus
    cached: bool


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class CheckRunner:
    store: CheckStore
    ledger: Ledger
    pipeline: Pipeline
    limiter: RateLimiter
    now: Callable[[], datetime] = _utcnow
    keep_channel_s: float = KEEP_CHANNEL_S
    channels: dict[UUID, Channel] = field(default_factory=dict)
    tasks: set[asyncio.Task[None]] = field(default_factory=set)

    async def submit(self, text: str, client: str, *, fresh: bool = False) -> Submitted:
        """Start a check of `text`. Raises ProblemError (429) when `client` is over its limit.
        `fresh` skips the ledger, so the claim is checked again (the seed's --force); the new
        result then becomes the ledger's newest entry for the claim."""
        started = self.now()
        hit = None if fresh else await self.ledger.lookup(text)
        if hit is not None:
            return await self._copy(text, CheckResult.model_validate(hit.entry.result), started)
        self._count(client)
        return await self._start(
            text, started, "No earlier check of this claim; checking it now.", None
        )

    async def recheck(
        self, original: CheckResult, index: int, indicator_id: str, client: str
    ) -> Submitted:
        """Check claim `index` of a finished check again with `indicator_id`, a statistic the
        claim offers. Counted like a new check; the result is never a ledger entry, so a plain
        check of the same words is never answered by a reader's choice."""
        claim = original.claims[index]
        self._count(client)
        first = claim.indicator
        replaced = Suggestion(id=first.id, name=first.name) if first else None
        offered = [*([first.id] if first else []), *(s.id for s in claim.suggestions)]
        work = Recheck(
            claim=claim.claim,
            choice=Choice(indicator_id, tuple(i for i in offered if i != indicator_id)),
            of=RecheckOf(check_id=original.id, claim_index=index, replaced=replaced),
        )
        return await self._start(
            claim.claim.quote, self.now(), "A re-check with another statistic.", work
        )

    def _count(self, client: str) -> None:
        wait = self.limiter.hit(client)
        if wait is not None:
            raise ProblemError(rate_limited(wait))

    async def _start(
        self, text: str, started: datetime, summary: str, recheck: Recheck | None
    ) -> Submitted:
        check_id = uuid4()
        await self.store.create(StoredCheck(check_id, text, CheckStatus.QUEUED, started))
        channel = self.channels[check_id] = Channel()
        await self._ledger_events(channel, summary)
        task = asyncio.create_task(self._run(check_id, text, started, channel, recheck))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        log.info("check_started", check_id=str(check_id), chars=len(text), recheck=bool(recheck))
        return Submitted(check_id, CheckStatus.QUEUED, cached=False)

    async def _copy(self, text: str, original: CheckResult, at: datetime) -> Submitted:
        """A new check id that serves an earlier result (its own permanent link)."""
        source = original.cached_from or original.id
        copy = original.model_copy(
            update={"id": uuid4(), "text": text, "created_at": at, "finished_at": at,
                    "cached_from": source}
        )  # fmt: skip
        await self.store.create(
            StoredCheck(
                copy.id, text, CheckStatus.DONE, at, finished_at=at,
                result=copy.model_dump(mode="json"), cached_from=source,
            )
        )  # fmt: skip
        channel = self.channels[copy.id] = Channel()
        await self._ledger_events(
            channel, f"Checked before on {original.created_at:%Y-%m-%d}; using that result."
        )
        await channel.publish("result", copy.model_dump(mode="json"))
        await self._finish_channel(copy.id, channel)
        log.info("check_cached", check_id=str(copy.id), cached_from=str(source))
        return Submitted(copy.id, CheckStatus.DONE, cached=True)

    @staticmethod
    async def _ledger_events(channel: Channel, summary: str) -> None:
        for event in ("step_started", "step_done"):
            step = StepEvent(
                event=event, step=Step.LEDGER, summary=summary if event == "step_done" else "",
                status="ok" if event == "step_done" else None,
                ms=0.0 if event == "step_done" else None,
            )  # fmt: skip
            await channel.publish(step.event, step.model_dump(mode="json"))

    async def _run(
        self,
        check_id: UUID,
        text: str,
        started: datetime,
        channel: Channel,
        recheck: Recheck | None = None,
    ) -> None:
        structlog.contextvars.bind_contextvars(check_id=str(check_id))

        async def emit(step: StepEvent) -> None:
            await channel.publish(step.event, step.model_dump(mode="json"))

        try:
            await self.store.mark_running(check_id)
            if recheck is None:
                output = await self.pipeline.run(text, emit)
            else:
                output = await self.pipeline.recheck(recheck.claim, recheck.choice, emit)
            result = CheckResult(
                id=check_id, text=text, created_at=started, finished_at=self.now(),
                claims=output.claims, versions=output.versions, models=output.models,
                notes=output.notes, recheck_of=recheck.of if recheck else None,
            )  # fmt: skip
            payload = result.model_dump(mode="json")
            reusable = recheck is None and not output.retryable
            entry = await self.ledger.entry(text, payload) if reusable else None
            await self.store.finish(result, entry)
            await channel.publish("result", payload)
            log.info("check_done", verdicts=[str(c.verdict.label) for c in result.claims])
        except RouterError as exc:
            log.warning("check_at_capacity", step=exc.step, attempts=exc.attempts)
            await self._fail(check_id, channel, at_capacity(exc.retry_after_s))
        except Exception:
            log.exception("check_failed")
            await self._fail(check_id, channel, internal_error())
        finally:
            await self._finish_channel(check_id, channel)

    async def _fail(self, check_id: UUID, channel: Channel, problem: Problem) -> None:
        try:
            await self.store.fail(check_id, problem, self.now())
        except Exception:
            log.exception("check_fail_not_stored")
        await channel.publish("error", problem.model_dump(mode="json", exclude_none=True))

    async def _finish_channel(self, check_id: UUID, channel: Channel) -> None:
        await channel.close()
        asyncio.get_running_loop().call_later(
            self.keep_channel_s, lambda: self.channels.pop(check_id, None)
        )

    async def exists(self, check_id: UUID) -> bool:
        return check_id in self.channels or await self.store.get(check_id) is not None

    async def events(self, check_id: UUID, after: int = -1) -> AsyncIterator[Event]:
        """The check's events after index `after`: live while it runs, else rebuilt from the
        stored check (just the `result` or `error`)."""
        channel = self.channels.get(check_id)
        if channel is not None:
            async for event in channel.follow(after):
                yield event
            return
        stored = await self.store.get(check_id)
        if stored is None:
            return
        # Always the final event, even after a Last-Event-ID: the stream must end with one.
        index = max(after + 1, 0)
        if stored.status is CheckStatus.DONE and stored.result is not None:
            yield Event(index, "result", stored.result)
        elif stored.status is CheckStatus.FAILED and stored.error is not None:
            yield Event(index, "error", stored.error)
        else:  # queued or running, but no task in this process: it died with a restart
            yield Event(index, "error", interrupted().model_dump(mode="json", exclude_none=True))

    async def shutdown(self) -> None:
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
