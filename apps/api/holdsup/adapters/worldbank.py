"""World Bank Indicators API v2. No key needed.

https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
Gotcha: a bad indicator code still returns HTTP 200, with a body like
`[{"message": [{"id": "120", "key": "Invalid value", "value": "..."}]}]`.
"""

import json
from datetime import UTC, datetime
from typing import cast

import httpx
from tenacity.wait import WaitBaseT

from holdsup.adapters.base import (
    FetchedSeries,
    Filters,
    Observation,
    SourceFormatError,
    SourceNotFound,
    sha256_hex,
)
from holdsup.adapters.http import DEFAULT_WAIT, get_with_retries

SOURCE = "worldbank"
BASE_URL = "https://api.worldbank.org/v2"
PER_PAGE = 1000
MAX_PAGES = 20

type JSON = None | bool | int | float | str | list["JSON"] | dict[str, "JSON"]


def _as_list(value: str | object) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(v) for v in cast(list[object], value)]


def error_message(doc: JSON) -> str | None:
    """The HTTP-200 error block, if this body is one."""
    if isinstance(doc, list) and doc and isinstance(doc[0], dict) and "message" in doc[0]:
        messages = doc[0]["message"]
        if isinstance(messages, list):
            parts = [
                f"{m.get('key', '')}: {m.get('value', '')} (id {m.get('id', '?')})"
                for m in messages
                if isinstance(m, dict)
            ]
            return "; ".join(parts) or "unknown error"
        return str(messages)
    return None


def _page(raw: bytes, indicator: str) -> tuple[dict[str, JSON], list[JSON]]:
    try:
        doc = cast(JSON, json.loads(raw))
    except json.JSONDecodeError as exc:
        raise SourceFormatError(f"worldbank {indicator}: not JSON") from exc
    if (message := error_message(doc)) is not None:
        raise SourceNotFound(f"worldbank {indicator}: {message}")
    if not isinstance(doc, list) or len(doc) != 2 or not isinstance(doc[0], dict):
        raise SourceFormatError(f"worldbank {indicator}: expected [meta, data]")
    meta, data = doc[0], doc[1]
    if data is None:
        return meta, []
    if not isinstance(data, list):
        raise SourceFormatError(f"worldbank {indicator}: data is not a list")
    return meta, data


def _observation(row: JSON, indicator: str) -> Observation:
    if not isinstance(row, dict):
        raise SourceFormatError(f"worldbank {indicator}: row is not an object")
    country, date, value = row.get("country"), row.get("date"), row.get("value")
    if not isinstance(country, dict) or not isinstance(date, str):
        raise SourceFormatError(f"worldbank {indicator}: row missing country/date")
    if value is not None and (isinstance(value, bool) or not isinstance(value, int | float)):
        raise SourceFormatError(f"worldbank {indicator}: non-numeric value {value!r}")
    status = row.get("obs_status")
    return Observation(
        geo=str(country.get("id")),
        period=date,
        value=float(value) if value is not None else None,
        status=str(status) if status else None,
        dims={"iso3": str(row.get("countryiso3code") or ""), "indicator": indicator},
    )


class WorldBankAdapter:
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
        """`dataset` is the indicator code; filters: `country` (ISO2/ISO3, one or many), `date`
        ("2010:2025" or "2020")."""
        countries = _as_list(filters.get("country", "all"))
        url = f"{self._base_url}/country/{';'.join(countries)}/indicator/{dataset}"
        params: dict[str, str] = {"format": "json", "per_page": str(PER_PAGE)}
        if "date" in filters:
            params["date"] = ";".join(_as_list(filters["date"]))

        bodies: list[bytes] = []
        rows: list[JSON] = []
        meta: dict[str, JSON] = {}
        first_url = ""
        page, pages = 1, 1
        while page <= pages:
            response = await get_with_retries(
                self._client,
                url,
                source=SOURCE,
                params={**params, "page": str(page)},
                retry_wait=self._retry_wait,
            )
            if response.status_code != 200:
                raise SourceNotFound(f"worldbank {dataset}: HTTP {response.status_code}")
            bodies.append(response.content)
            first_url = first_url or str(response.request.url)
            meta, data = _page(response.content, dataset)
            rows.extend(data)
            reported = meta.get("pages")
            pages = min(reported if isinstance(reported, int) else 1, MAX_PAGES)
            page += 1

        obs = [_observation(r, dataset) for r in rows]
        if not any(o.value is not None for o in obs):
            raise SourceNotFound(f"worldbank {dataset}: no values for {dict(filters)}")
        obs.sort(key=lambda o: (o.geo, o.period))
        label = ""
        first = rows[0]
        if isinstance(first, dict) and isinstance(first.get("indicator"), dict):
            label = str(cast(dict[str, JSON], first["indicator"]).get("value", ""))
        updated = meta.get("lastupdated")
        return FetchedSeries(
            source=SOURCE,
            dataset=dataset,
            url=first_url,
            retrieved_at=datetime.now(UTC),
            raw_sha256=sha256_hex(*bodies),
            observations=obs,
            label=label,
            updated=str(updated) if updated else None,
            citation=f"World Bank, World Development Indicators ({dataset})",
        )
