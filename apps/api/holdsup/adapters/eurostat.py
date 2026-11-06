"""Eurostat dissemination API (JSON-stat 2.0). No key needed.

https://wikis.ec.europa.eu/display/EUROSTATHELP/API+Statistics+-+data+query
"""

import json
from datetime import UTC, datetime

import httpx
from tenacity.wait import WaitBaseT

from holdsup.adapters.base import (
    FetchedSeries,
    Filters,
    SourceFormatError,
    SourceNotFound,
    sha256_hex,
)
from holdsup.adapters.http import DEFAULT_WAIT, get_with_retries
from holdsup.adapters.jsonstat import observations, parse_cube

SOURCE = "eurostat"
BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


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
    source = SOURCE

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = BASE_URL,
        retry_wait: WaitBaseT = DEFAULT_WAIT,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._retry_wait = retry_wait

    async def fetch_series(self, dataset: str, filters: Filters) -> FetchedSeries:
        response = await get_with_retries(
            self._client,
            f"{self._base_url}/{dataset}",
            source=SOURCE,
            params=build_params(filters),
            retry_wait=self._retry_wait,
        )
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
            citation=f"Eurostat ({dataset})",
        )
