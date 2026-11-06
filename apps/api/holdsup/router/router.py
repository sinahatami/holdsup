"""Pick a provider per call, track budgets, fail over on limits, errors, and bad output."""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import overload

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolUnionParam,
)
from openai.types.chat.completion_create_params import ResponseFormat
from pydantic import BaseModel, ValidationError

from holdsup.router.breaker import CircuitBreaker
from holdsup.router.budgets import Budgets, InMemoryUsageStore, UsageStore
from holdsup.router.client import ChatRequest, ChatResponse, SupportsChat, ToolCall
from holdsup.router.clock import Clock, SystemClock, next_utc_midnight
from holdsup.router.config import Capability, ProviderConfig, RouterConfig, Use
from holdsup.router.errors import (
    MalformedOutput,
    ProviderError,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    RateLimited,
    RouterError,
)

log = logging.getLogger("holdsup.router")

DEFAULT_COOLDOWN_S = 60.0
MAX_PACING_WAIT_S = 2.0  # wait out min_interval_s gaps up to this long instead of skipping
SCHEMA_RETRIES = 1


@dataclass(frozen=True)
class Attempt:
    provider: str
    outcome: str  # ok | rate_limited | daily_limit | timeout | unavailable | rejected | malformed
    latency_ms: float
    detail: str = ""


@dataclass(frozen=True)
class RouterResult[T: BaseModel]:
    provider: str
    model: str
    content: str | None
    parsed: T | None
    tool_calls: tuple[ToolCall, ...]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    attempts: tuple[Attempt, ...] = field(default_factory=tuple)


class Router:
    def __init__(
        self,
        config: RouterConfig,
        client: SupportsChat,
        usage_store: UsageStore | None = None,
        clock: Clock | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.config = config
        self._client = client
        self._clock = clock or SystemClock()
        self._sleep = sleep
        self._last_call: dict[str, float] = {}
        self.budgets = Budgets(usage_store or InMemoryUsageStore())
        self.breaker = breaker or CircuitBreaker()
        self._cooldown_until: dict[str, float] = {}
        self._exhausted_until: dict[str, float] = {}

    # --- eligibility -------------------------------------------------------------------------

    def _needs(self, schema: type[BaseModel] | None, tools: object) -> set[Capability]:
        needs: set[Capability] = set()
        if schema is not None:
            needs.add(Capability.JSON_OBJECT)
        if tools:
            needs.add(Capability.TOOLS)
        return needs

    @staticmethod
    def _capable(provider: ProviderConfig, needs: set[Capability]) -> bool:
        caps = set(provider.capabilities)
        if Capability.JSON_SCHEMA in caps:
            caps.add(Capability.JSON_OBJECT)  # schema mode implies JSON output
        return needs <= caps

    def _pacing_s(self, provider: ProviderConfig, now: float) -> float:
        """Seconds until `min_interval_s` since the last call to this provider has passed."""
        last = self._last_call.get(provider.name)
        return 0.0 if last is None else max(0.0, last + provider.min_interval_s - now)

    async def _ready(self, provider: ProviderConfig) -> float:
        """Wait out a short pacing gap; return 0 if callable now, else seconds to wait."""
        now = self._clock.now()
        wait = await self._wait_s(provider, now)
        pacing = self._pacing_s(provider, now)
        if wait > 0 and wait <= pacing <= MAX_PACING_WAIT_S:
            await self._sleep(pacing)
            return await self._wait_s(provider, self._clock.now())
        return wait

    async def _wait_s(self, provider: ProviderConfig, now: float) -> float:
        """0 if the provider can be called now, else seconds until it might be."""
        waits = [
            self._pacing_s(provider, now),
            self._cooldown_until.get(provider.name, 0.0) - now,
            self._exhausted_until.get(provider.name, 0.0) - now,
            self.breaker.wait_s(provider.name, now),
            self.budgets.minute_wait_s(provider, now),
        ]
        if await self.budgets.day_exhausted(provider, now):
            waits.append(next_utc_midnight(now) - now)
        return max(0.0, *waits)

    def candidates(self, step: str, use: Use, needs: set[Capability]) -> list[ProviderConfig]:
        """Providers for this step, in preference order, allowed for `use` and capable."""
        if step not in self.config.steps:
            raise KeyError(f"unknown step {step!r}")
        out = []
        for name in self.config.steps[step]:
            p = self.config.provider(name)
            if p.serves(use) and self._capable(p, needs) and self._client.has_key(p):
                out.append(p)
        return out

    # --- the call ------------------------------------------------------------------------------

    @overload
    async def complete[T: BaseModel](
        self,
        step: str,
        messages: Sequence[ChatCompletionMessageParam],
        *,
        use: Use,
        schema: type[T],
        tools: Sequence[ChatCompletionToolUnionParam] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> RouterResult[T]: ...

    @overload
    async def complete(
        self,
        step: str,
        messages: Sequence[ChatCompletionMessageParam],
        *,
        use: Use,
        schema: None = None,
        tools: Sequence[ChatCompletionToolUnionParam] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> RouterResult[BaseModel]: ...

    async def complete[T: BaseModel](
        self,
        step: str,
        messages: Sequence[ChatCompletionMessageParam],
        *,
        use: Use,
        schema: type[T] | None = None,
        tools: Sequence[ChatCompletionToolUnionParam] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> RouterResult[T]:
        attempts: list[Attempt] = []
        waits: list[float] = []
        for provider in self.candidates(step, use, self._needs(schema, tools)):
            wait = await self._ready(provider)
            if wait > 0:
                waits.append(wait)
                continue
            result = await self._try_provider(
                provider, messages, schema, tools, tool_choice, attempts
            )
            if result is not None:
                return result
            waits.append(await self._wait_s(provider, self._clock.now()))
        raise RouterError(
            step=step,
            attempts=[f"{a.provider}:{a.outcome}" for a in attempts],
            retry_after_s=min((w for w in waits if w > 0), default=None),
            details=[f"{a.provider} {a.outcome}: {a.detail}" for a in attempts if a.detail],
        )

    async def _try_provider[T: BaseModel](
        self,
        provider: ProviderConfig,
        messages: Sequence[ChatCompletionMessageParam],
        schema: type[T] | None,
        tools: Sequence[ChatCompletionToolUnionParam] | None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None,
        attempts: list[Attempt],
    ) -> RouterResult[T] | None:
        convo = list(messages)
        response_format = _response_format(provider, schema)
        if schema is not None and response_format == {"type": "json_object"}:
            convo.insert(0, _schema_instruction(schema))

        for schema_try in range(SCHEMA_RETRIES + 1):
            if schema_try > 0 and await self._ready(provider) > 0:
                return None
            request = ChatRequest(
                messages=convo,
                response_format=response_format,
                tools=tools,
                tool_choice=tool_choice,
            )
            started = time.perf_counter()
            self._last_call[provider.name] = self._clock.now()
            await self.budgets.record(provider, self._clock.now())
            try:
                response = await self._client.complete(provider, request)
            except ProviderError as exc:
                latency = _ms(started)
                attempts.append(self._on_failure(provider, exc, latency))
                return None
            latency = _ms(started)
            self.breaker.record_success(provider.name)
            await self.budgets.add_tokens(
                provider, self._clock.now(), response.prompt_tokens + response.completion_tokens
            )

            try:
                parsed = _parse(response, schema)
            except MalformedOutput as exc:
                attempts.append(Attempt(provider.name, "malformed", latency, str(exc)[:300]))
                log.info("router.malformed provider=%s try=%d", provider.name, schema_try)
                convo = [*convo, *_repair_messages(response, exc)]
                continue

            attempts.append(Attempt(provider.name, "ok", latency))
            return RouterResult(
                provider=provider.name,
                model=provider.model,
                content=response.content,
                parsed=parsed,
                tool_calls=response.tool_calls,
                latency_ms=latency,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                attempts=tuple(attempts),
            )
        return None

    def _on_failure(self, provider: ProviderConfig, exc: ProviderError, latency: float) -> Attempt:
        now = self._clock.now()
        name = provider.name
        match exc:
            case RateLimited(daily=True):
                self._exhausted_until[name] = next_utc_midnight(now)
                outcome = "daily_limit"
            case RateLimited(retry_after_s=retry_after):
                self._cooldown_until[name] = now + (
                    retry_after if retry_after is not None else DEFAULT_COOLDOWN_S
                )
                outcome = "rate_limited"
            case ProviderTimeout():
                self.breaker.record_failure(name, now)
                outcome = "timeout"
            case ProviderUnavailable():
                self.breaker.record_failure(name, now)
                outcome = "unavailable"
            case ProviderRejected():
                self.breaker.record_failure(name, now)
                outcome = "rejected"
            case _:
                self.breaker.record_failure(name, now)
                outcome = "error"
        log.warning("router.failure provider=%s outcome=%s", name, outcome)
        return Attempt(name, outcome, latency, str(exc)[:300])


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def _response_format(
    provider: ProviderConfig, schema: type[BaseModel] | None
) -> ResponseFormat | None:
    if schema is None:
        return None
    if Capability.JSON_SCHEMA in provider.capabilities:
        return {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
        }
    return {"type": "json_object"}


def _schema_instruction(schema: type[BaseModel]) -> ChatCompletionMessageParam:
    return {
        "role": "system",
        "content": "Reply with a single JSON object that matches this JSON Schema:\n"
        + json.dumps(schema.model_json_schema()),
    }


def _parse[T: BaseModel](response: ChatResponse, schema: type[T] | None) -> T | None:
    if schema is None:
        return None
    if not response.content:
        raise MalformedOutput("empty response; expected JSON")
    try:
        return schema.model_validate_json(response.content)
    except ValidationError as exc:
        raise MalformedOutput(str(exc)) from exc


def _repair_messages(
    response: ChatResponse, exc: MalformedOutput
) -> list[ChatCompletionMessageParam]:
    return [
        {"role": "assistant", "content": response.content or ""},
        {
            "role": "user",
            "content": "That reply was not valid for the required JSON Schema. Error:\n"
            f"{str(exc)[:1000]}\nReply again with only the corrected JSON object.",
        },
    ]
