"""A router that waits out a rate limit and retries the one call that hit it.

An evaluation run sends a few hundred calls through free-tier providers in minutes, so rate
limits are expected, not exceptional. The production router answers a limit by failing over and,
when every provider is cooling down, by raising RouterError with the shortest wait. Retrying the
whole text after that (the earlier fix) re-runs the steps that had already worked and spends the
per-minute budget again; waiting here resumes at the step that failed.

A wait over `max_wait_s` (a daily quota) is not waited for, and the run as a whole waits at most
`budget_s`: past that the error is raised and the text is recorded as not run.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from holdsup.router import Router, RouterError, RouterResult, Use
from holdsup.router.client import SupportsChat
from holdsup.router.config import RouterConfig

MAX_WAIT_S = 90.0
BUDGET_S = 600.0
CALL_RETRIES = 8

Progress = Callable[[str], None]


class PatientRouter(Router):
    def __init__(
        self,
        config: RouterConfig,
        client: SupportsChat,
        *,
        max_wait_s: float = MAX_WAIT_S,
        budget_s: float = BUDGET_S,
        call_retries: int = CALL_RETRIES,
        wait: Callable[[float], Awaitable[None]] = asyncio.sleep,
        progress: Progress = lambda _: None,
        **kwargs: Any,
    ) -> None:
        super().__init__(config, client, **kwargs)
        self._max_wait_s = max_wait_s
        self._call_retries = call_retries
        self._wait = wait
        self._progress = progress
        self.budget_left_s = budget_s

    async def complete(
        self,
        step: str,
        messages: Sequence[ChatCompletionMessageParam],
        *,
        use: Use,
        schema: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> RouterResult[Any]:
        for attempt in range(self._call_retries + 1):
            try:
                return await super().complete(step, messages, use=use, schema=schema, **kwargs)
            except RouterError as exc:
                seconds = (exc.retry_after_s or 0.0) + 1.0
                if (
                    attempt == self._call_retries
                    or exc.retry_after_s is None
                    or exc.retry_after_s > self._max_wait_s
                    or seconds > self.budget_left_s
                ):
                    raise
                self.budget_left_s -= seconds
                self._progress(f"  waiting {seconds:.0f}s at {step!r} ({attempt + 1})")
                await self._wait(seconds)
        raise AssertionError("unreachable")  # pragma: no cover
