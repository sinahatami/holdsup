"""Eurostat dissemination API (JSON-stat 2.0). No key needed.

https://wikis.ec.europa.eu/display/EUROSTATHELP/API+Statistics+-+data+query
"""

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import WaitBaseT

from holdsup.adapters.base import (
    FetchedSeries,
    SourceFormatError,
    SourceNotFound,
    SourceUnavailable,
    sha256_hex,
)
from holdsup.adapters.jsonstat import observations, parse_cube

SOURCE = "eurostat"
BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
TIMEOUT_S = 30.0
ATTEMPTS = 3
DEFAULT_WAIT = wait_exponential(multiplier=0.5, max=4)

Filters = Mapping[str, str | Sequence[str]]


class _Transient(Exception):
    pass


def build_params(filters: Filters) -> dict[str, list[str]]:
    """Query parameters; a list value repeats the key (geo=IT&geo=DE)."""
    params: dict[str, list[str]] = {"format": ["JSON"], "lang": ["EN"]}
    for key in sorted(filters):
        value = filters[key]
        params[key] = [value] if isinstance(value, str) else list(value)
    return params


def _error_label(body: bytes) -> str:
    try:
        doc = json.loads(body)
        return "; ".join(str(e.get("label", "")) for e in doc.get("error", []))
    except (ValueError, AttributeError, TypeError):
        return body[:200].decode("utf-8", "replace")


class EurostatAdapter:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = BASE_URL,
        retry_wait: WaitBaseT = DEFAULT_WAIT,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._retry_wait = retry_wait

    async def _get(self, url: str, params: dict[str, list[str]]) -> httpx.Response:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(ATTEMPTS),
                wait=self._retry_wait,
                retry=retry_if_exception_type(_Transient),
                reraise=True,
            ):
                with attempt:
                    try:
                        response = await self._client.get(url, params=params, timeout=TIMEOUT_S)
                    except httpx.TransportError as exc:
                        raise _Transient(str(exc)) from exc
                    if response.status_code >= 500 or response.status_code == 429:
                        raise _Transient(f"HTTP {response.status_code}")
                    return response
        except _Transient as exc:
            raise SourceUnavailable(f"eurostat: {exc}") from exc
        raise AssertionError("unreachable")  # pragma: no cover

    async def fetch_series(self, dataset: str, filters: Filters) -> FetchedSeries:
        url = f"{self._base_url}/{dataset}"
        params = build_params(filters)
        response = await self._get(url, params)
        if response.status_code in (400, 404):
            raise SourceNotFound(f"eurostat {dataset}: {_error_label(response.content)}")
        if response.status_code != 200:
            raise SourceFormatError(f"eurostat {dataset}: unexpected HTTP {response.status_code}")

        cube = parse_cube(response.content)
        obs = observations(cube)
        if not any(o.value is not None for o in obs):
            raise SourceNotFound(f"eurostat {dataset}: no values for {dict(filters)}")
        return FetchedSeries(
            source=SOURCE,
            dataset=dataset,
            url=str(response.request.url),
            retrieved_at=datetime.now(UTC),
            raw_sha256=sha256_hex(response.content),
            observations=obs,
            label=cube.label,
            dimension_labels=cube.labels,
            status_labels=cube.status_labels,
            updated=cube.updated,
        )
