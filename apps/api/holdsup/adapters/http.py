"""GET with retries on transient failures, shared by every adapter."""

from collections.abc import Mapping, Sequence

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential
from tenacity.wait import WaitBaseT

from holdsup.adapters.base import SourceUnavailable

TIMEOUT_S = 30.0
ATTEMPTS = 3
DEFAULT_WAIT = wait_exponential(multiplier=0.5, max=4)

Params = Mapping[str, str | Sequence[str]]


class _Transient(Exception):
    pass


async def get_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    source: str,
    params: Params | None = None,
    retry_wait: WaitBaseT = DEFAULT_WAIT,
) -> httpx.Response:
    """Retry transport errors, 5xx, and 429; return any other response for the caller to judge."""
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(ATTEMPTS),
            wait=retry_wait,
            retry=retry_if_exception_type(_Transient),
            reraise=True,
        ):
            with attempt:
                try:
                    response = await client.get(
                        url, params=params, timeout=TIMEOUT_S, follow_redirects=True
                    )
                except httpx.TransportError as exc:
                    raise _Transient(str(exc) or type(exc).__name__) from exc
                if response.status_code >= 500 or response.status_code == 429:
                    raise _Transient(f"HTTP {response.status_code}")
                return response
    except _Transient as exc:
        raise SourceUnavailable(f"{source}: {exc}") from exc
    raise AssertionError("unreachable")  # pragma: no cover
