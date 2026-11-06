"""The OpenAI-compatible client against recorded-style HTTP responses (httpx2.MockTransport).

These check that real provider HTTP failures map to the router's typed errors.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import format_datetime

import httpx2
import pytest

from holdsup.router.client import (
    ChatRequest,
    OpenAICompatibleClient,
    is_daily_limit,
    parse_retry_after,
)
from holdsup.router.config import ProviderConfig
from holdsup.router.errors import (
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    RateLimited,
)
from tests.router.fakes import T0, FakeClock, config, provider

Handler = Callable[[httpx2.Request], httpx2.Response]

PROVIDER: ProviderConfig = config(provider("groq")).providers[0]
REQUEST = ChatRequest(messages=[{"role": "user", "content": "hi"}])

COMPLETION = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 1_793_966_400,
    "model": "groq-model",
    "choices": [
        {
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": '{"ok": true}'},
        }
    ],
    "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
}


def client_for(handler: Handler, *, env: dict[str, str] | None = None) -> OpenAICompatibleClient:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return OpenAICompatibleClient(
        env={"GROQ_KEY": "test-key"} if env is None else env,
        http_client=http,
        clock=FakeClock(),
    )


def error(status: int, message: str, headers: dict[str, str] | None = None) -> Handler:
    body = {"error": {"message": message, "type": "error", "code": str(status)}}
    return lambda _: httpx2.Response(status, json=body, headers=headers)


async def test_success_returns_content_usage_and_sends_expected_request() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=COMPLETION)

    response = await client_for(handler).complete(
        PROVIDER, ChatRequest(messages=REQUEST.messages, response_format={"type": "json_object"})
    )

    assert response.content == '{"ok": true}'
    assert (response.prompt_tokens, response.completion_tokens) == (12, 4)
    sent = json.loads(seen[0].content)
    assert seen[0].url == "https://example.invalid/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer test-key"
    assert sent["model"] == "groq-model"
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["temperature"] == 0.0
    assert "tools" not in sent
    assert "tool_choice" not in sent


async def test_tool_calls_are_returned() -> None:
    body = json.loads(json.dumps(COMPLETION))
    body["choices"][0]["message"] = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "search_catalog", "arguments": '{"q": "youth unemployment"}'},
            }
        ],
    }
    del body["usage"]
    seen: list[dict[str, object]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(json.loads(request.content))
        return httpx2.Response(200, json=body)

    tools = [{"type": "function", "function": {"name": "search_catalog", "parameters": {}}}]
    response = await client_for(handler).complete(
        PROVIDER,
        ChatRequest(messages=REQUEST.messages, tools=tools, tool_choice="auto"),  # type: ignore[arg-type]
    )

    assert response.content is None
    assert [(c.name, c.arguments) for c in response.tool_calls] == [
        ("search_catalog", '{"q": "youth unemployment"}')
    ]
    assert response.prompt_tokens == 0
    assert seen[0]["tool_choice"] == "auto"


async def test_429_with_retry_after_header() -> None:
    client = client_for(
        error(429, "Rate limit reached: requests per minute (RPM)", {"retry-after": "7"})
    )
    with pytest.raises(RateLimited) as info:
        await client.complete(PROVIDER, REQUEST)
    assert info.value.retry_after_s == 7
    assert info.value.daily is False


async def test_429_without_retry_after_header() -> None:
    with pytest.raises(RateLimited) as info:
        await client_for(error(429, "Too many requests")).complete(PROVIDER, REQUEST)
    assert info.value.retry_after_s is None
    assert info.value.daily is False


@pytest.mark.parametrize(
    "message",
    [
        "Rate limit reached for model `llama-3.3-70b-versatile` on requests per day (RPD): Limit 1000",
        "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests",
    ],
)
async def test_429_daily_quota_is_detected(message: str) -> None:
    with pytest.raises(RateLimited) as info:
        await client_for(error(429, message, {"retry-after": "3600"})).complete(PROVIDER, REQUEST)
    assert info.value.daily is True


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_5xx_is_unavailable(status: int) -> None:
    with pytest.raises(ProviderUnavailable):
        await client_for(error(status, "upstream error")).complete(PROVIDER, REQUEST)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
async def test_other_4xx_is_rejected(status: int) -> None:
    with pytest.raises(ProviderRejected, match=f"HTTP {status}"):
        await client_for(error(status, "nope")).complete(PROVIDER, REQUEST)


async def test_timeout() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    with pytest.raises(ProviderTimeout):
        await client_for(handler).complete(PROVIDER, REQUEST)


async def test_connection_error() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(ProviderUnavailable):
        await client_for(handler).complete(PROVIDER, REQUEST)


async def test_malformed_json_body_is_unavailable() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, content=b"<html>gateway</html>", headers={"content-type": "application/json"}
        )

    with pytest.raises(ProviderUnavailable, match="unparseable"):
        await client_for(handler).complete(PROVIDER, REQUEST)


async def test_response_without_choices_is_unavailable() -> None:
    with pytest.raises(ProviderUnavailable, match="no choices"):
        await client_for(lambda _: httpx2.Response(200, json={"id": "x"})).complete(
            PROVIDER, REQUEST
        )


async def test_missing_api_key_is_rejected_without_a_request() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        raise AssertionError("must not be called")

    client = client_for(handler, env={})
    assert client.has_key(PROVIDER) is False
    with pytest.raises(ProviderRejected, match="GROQ_KEY"):
        await client.complete(PROVIDER, REQUEST)


def test_parse_retry_after_variants() -> None:
    assert parse_retry_after({"retry-after": "12"}, T0) == 12
    assert parse_retry_after({"retry-after-ms": "1500", "retry-after": "9"}, T0) == 1.5
    assert parse_retry_after({"retry-after-ms": "soon", "retry-after": "9"}, T0) == 9
    date = format_datetime(datetime.fromtimestamp(T0 + 30, UTC), usegmt=True)
    assert parse_retry_after({"retry-after": date}, T0) == pytest.approx(30)
    assert parse_retry_after({"retry-after": "whenever"}, T0) is None
    assert parse_retry_after({}, T0) is None


def test_is_daily_limit() -> None:
    assert is_daily_limit("Limit on tokens per day (TPD)")
    assert not is_daily_limit("Rate limit reached: requests per minute (RPM)")
