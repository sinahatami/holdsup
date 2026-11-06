"""Chat client over each provider's OpenAI-compatible endpoint (the only provider SDK use).

SDK retries are disabled: the router owns retries, cool-downs, and fallbacks.
"""

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Protocol

import httpx2
import openai
from openai import AsyncOpenAI, omit
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolUnionParam,
)
from openai.types.chat.completion_create_params import ResponseFormat

from holdsup.router.clock import Clock, SystemClock
from holdsup.router.config import ProviderConfig
from holdsup.router.errors import (
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    RateLimited,
)

# Phrases providers use when the *daily* quota (not the per-minute one) is spent.
_DAILY_PATTERN = re.compile(
    r"per[ -]?day|requests per day|\bRPD\b|\bTPD\b|daily|free-models-per-day", re.IGNORECASE
)


@dataclass(frozen=True)
class ChatRequest:
    messages: Sequence[ChatCompletionMessageParam]
    response_format: ResponseFormat | None = None
    tools: Sequence[ChatCompletionToolUnionParam] | None = None
    tool_choice: ChatCompletionToolChoiceOptionParam | None = None
    temperature: float = 0.0


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ChatResponse:
    content: str | None
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class SupportsChat(Protocol):
    """What the router needs from a client. Tests use fakes; production uses the one below."""

    def has_key(self, provider: ProviderConfig) -> bool: ...

    async def complete(self, provider: ProviderConfig, request: ChatRequest) -> ChatResponse: ...


def parse_retry_after(headers: Mapping[str, str], now: float) -> float | None:
    """Seconds to wait, from `retry-after-ms`, `retry-after` (seconds or HTTP date)."""
    if (ms := headers.get("retry-after-ms")) is not None:
        try:
            return max(0.0, float(ms) / 1000)
        except ValueError:
            pass
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - now)
    except (TypeError, ValueError):
        return None


def is_daily_limit(message: str) -> bool:
    return bool(_DAILY_PATTERN.search(message))


class OpenAICompatibleClient:
    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        http_client: httpx2.AsyncClient | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._env = os.environ if env is None else env
        self._http_client = http_client
        self._clock = clock or SystemClock()
        self._clients: dict[str, AsyncOpenAI] = {}

    def has_key(self, provider: ProviderConfig) -> bool:
        return bool(self._env.get(provider.api_key_env))

    def _client(self, provider: ProviderConfig) -> AsyncOpenAI:
        if provider.name not in self._clients:
            api_key = self._env.get(provider.api_key_env)
            if not api_key:
                raise ProviderRejected(f"{provider.api_key_env} is not set")
            self._clients[provider.name] = AsyncOpenAI(
                api_key=api_key,
                base_url=provider.base_url,
                timeout=provider.timeout_s,
                max_retries=0,
                http_client=self._http_client,
            )
        return self._clients[provider.name]

    async def complete(self, provider: ProviderConfig, request: ChatRequest) -> ChatResponse:
        client = self._client(provider)
        try:
            completion = await client.chat.completions.create(
                model=provider.model,
                messages=list(request.messages),
                temperature=request.temperature,
                response_format=request.response_format or omit,
                tools=list(request.tools) if request.tools else omit,
                tool_choice=request.tool_choice if request.tools and request.tool_choice else omit,
            )
        except openai.RateLimitError as exc:
            message = _error_message(exc)
            raise RateLimited(
                retry_after_s=parse_retry_after(exc.response.headers, self._clock.now()),
                daily=is_daily_limit(message),
                message=message,
            ) from exc
        except openai.APITimeoutError as exc:
            raise ProviderTimeout(str(exc)) from exc
        except openai.APIConnectionError as exc:
            raise ProviderUnavailable(str(exc)) from exc
        except openai.InternalServerError as exc:
            raise ProviderUnavailable(_error_message(exc)) from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise ProviderUnavailable(_error_message(exc)) from exc
            raise ProviderRejected(f"HTTP {exc.status_code}: {_error_message(exc)}") from exc
        except (openai.APIResponseValidationError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"unparseable response: {exc}") from exc

        if not completion.choices:
            raise ProviderUnavailable("response has no choices")
        reply = completion.choices[0].message
        tool_calls = tuple(
            ToolCall(id=c.id, name=c.function.name, arguments=c.function.arguments)
            for c in (reply.tool_calls or [])
            if c.type == "function"
        )
        usage = completion.usage
        return ChatResponse(
            content=reply.content,
            tool_calls=tool_calls,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )


def _error_message(exc: openai.APIStatusError) -> str:
    try:
        return exc.response.text[:500]
    except Exception:  # noqa: BLE001  # response body may be unreadable; fall back to str()
        return str(exc)
