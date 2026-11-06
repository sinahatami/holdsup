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
    model_not_on_plan,
    parse_retry_after,
    provider_message,
    rate_limit_headers,
)
from holdsup.router.config import ProviderConfig, load_router_config
from holdsup.router.errors import (
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    RateLimited,
)
from holdsup.router.redact import REDACTED, redact, secret_values
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


# --- endpoint, error detail, redaction (provider smoke fix) -----------------------------------


@pytest.mark.parametrize("p", load_router_config().providers, ids=lambda p: p.name)
async def test_every_configured_provider_uses_chat_completions(p: ProviderConfig) -> None:
    """The client must call <base_url>/chat/completions (OpenAI-compatible), never /responses."""
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=COMPLETION)

    client = client_for(handler, env={p.api_key_env: "test-key"})
    await client.complete(p, REQUEST)

    base_path = httpx2.URL(p.base_url).path.rstrip("/")
    assert seen[0].method == "POST"
    assert seen[0].url.host == httpx2.URL(p.base_url).host
    assert seen[0].url.path == f"{base_path}/chat/completions"
    assert "/responses" not in seen[0].url.path
    assert json.loads(seen[0].content)["model"] == p.model


async def test_rejected_error_carries_status_and_provider_message() -> None:
    body = {"error": {"message": "The model `x` does not exist or you do not have access to it."}}
    client = client_for(lambda _: httpx2.Response(404, json=body))
    with pytest.raises(ProviderRejected) as info:
        await client.complete(PROVIDER, REQUEST)
    assert (
        str(info.value) == "HTTP 404: The model `x` does not exist or you do not have access to it."
    )


async def test_api_key_echoed_in_error_body_is_redacted() -> None:
    key = "gsk_" + "A1b2C3d4" * 6
    body = {"error": {"message": f"Invalid API Key: {key} (also sk-or-v1-{'f' * 40})"}}
    client = client_for(lambda _: httpx2.Response(401, json=body), env={"GROQ_KEY": key})
    with pytest.raises(ProviderRejected) as info:
        await client.complete(PROVIDER, REQUEST)
    text = str(info.value)
    assert key not in text
    assert "sk-or-v1-" not in text
    assert text.count(REDACTED) == 2


async def test_429_with_zero_limit_is_treated_as_not_on_plan() -> None:
    headers = {"x-ratelimit-limit-req-minute": "0", "x-ratelimit-remaining-req-minute": "0"}
    client = client_for(error(429, "Rate limit exceeded", headers))
    with pytest.raises(RateLimited) as info:
        await client.complete(PROVIDER, REQUEST)
    assert info.value.daily is True  # router marks it exhausted, no 60 s retry loop
    assert "x-ratelimit-limit-req-minute=0" in str(info.value)
    assert "not available on this plan" in str(info.value)


async def test_openrouter_upstream_error_is_shown() -> None:
    body = {
        "error": {
            "message": "Provider returned error",
            "code": 429,
            "metadata": {"provider_name": "Google AI Studio", "raw": "temporarily rate-limited"},
        }
    }
    with pytest.raises(RateLimited) as info:
        await client_for(lambda _: httpx2.Response(429, json=body)).complete(PROVIDER, REQUEST)
    assert "upstream=Google AI Studio; raw=temporarily rate-limited" in str(info.value)
    assert info.value.daily is False


def test_provider_message_shapes() -> None:
    assert provider_message('{"message": "mistral style"}') == "mistral style"
    assert provider_message('{"detail": "fastapi style"}') == "fastapi style"
    assert provider_message('[{"error": {"message": "gemini style"}}]') == "gemini style"
    assert provider_message('{"error": "plain string"}') == "plain string"
    assert provider_message('{"detail": [{"loc": ["model"]}]}') == '[{"loc": ["model"]}]'
    assert provider_message('{"other": 1}') == '{"other": 1}'
    assert provider_message("  not json  ") == "not json"


def test_rate_limit_headers_and_zero_limit() -> None:
    headers = {"X-RateLimit-Limit-Requests": "1000", "Retry-After": "2", "content-type": "json"}
    assert rate_limit_headers(headers) == "retry-after=2, x-ratelimit-limit-requests=1000"
    assert not model_not_on_plan(headers)
    assert model_not_on_plan({"x-ratelimit-limit-tokens-minute": " 0 "})


def test_redact() -> None:
    assert redact("key=supersecretvalue", ["supersecretvalue"]) == f"key={REDACTED}"
    assert redact("Authorization: Bearer abcdefghijk") == f"Authorization: {REDACTED}"
    assert redact("AIza" + "x" * 35) == REDACTED
    assert redact("nothing here") == "nothing here"
    env = {
        "GROQ_API_KEY": "long-enough-secret",
        "SHORT_API_KEY": "abc",
        "HF_TOKEN": "hf_tokenvalue1",
    }
    assert sorted(secret_values(env)) == ["hf_tokenvalue1", "long-enough-secret"]


async def test_list_models() -> None:
    body = {
        "object": "list",
        "data": [
            {
                "id": "models/gemini-3.5-flash",
                "object": "model",
                "created": 0,
                "owned_by": "google",
            },
            {
                "id": "a:free",
                "object": "model",
                "created": 0,
                "owned_by": "x",
                "context_length": 1000,
                "supported_parameters": ["tools", "response_format"],
            },
        ],
    }
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=body)

    models = await client_for(handler).list_models(PROVIDER)
    assert seen[0].url.path == "/v1/models"
    assert [m.id for m in models] == ["a:free", "gemini-3.5-flash"]
    assert models[0].context == 1000
    assert models[0].supported_parameters == ("tools", "response_format")


async def test_list_models_errors() -> None:
    with pytest.raises(ProviderRejected, match="HTTP 401: bad key"):
        await client_for(error(401, "bad key")).list_models(PROVIDER)

    def boom(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(ProviderUnavailable):
        await client_for(boom).list_models(PROVIDER)
