"""Shared helpers for adapter tests: serve recorded fixtures through httpx.MockTransport."""

from collections.abc import Callable
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
Handler = Callable[[httpx.Request], httpx.Response]


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def mock_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def serve(
    body: bytes,
    status: int = 200,
    seen: list[httpx.Request] | None = None,
    content_type: str = "application/json",
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, content=body, headers={"content-type": content_type})

    return handler
