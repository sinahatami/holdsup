"""Our World in Data chart API: `<chart>.csv` and `<chart>.metadata.json`. No key; CC BY 4.0.

https://docs.owid.io/projects/etl/api/chart-api/
Gotchas:
- Charts whose data is not redistributable answer HTTP 403; we raise a typed error.
- The filtered CSV follows the chart's default tab. On a map-first chart it is the map's
  one-year snapshot of every country and ignores `country` and `time`, so we always ask for
  `tab=chart` and also filter countries and years ourselves.
- Multi-view charts (e.g. `energy-mix`) need their view options (`metric`, `source`, ...) in
  the query; old slugs redirect to such a view (`renewable-share-energy` →
  `energy-mix?metric=share&source=renewables`) but their metadata URL is a 404, so metadata
  is fetched from the chart and view the CSV request ended up at.
"""

import csv
import io
import json
import math
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast
from urllib.parse import unquote

import httpx
from tenacity.wait import WaitBaseT

from holdsup.adapters.base import (
    FetchedSeries,
    Filters,
    Observation,
    SourceFormatError,
    SourceNotFound,
    SourceNotRedistributable,
    sha256_hex,
)
from holdsup.adapters.http import DEFAULT_WAIT, get_with_retries

SOURCE = "owid"
BASE_URL = "https://ourworldindata.org/grapher"
_KEY_COLUMNS = {"entity", "code", "year", "day"}
# Filters the adapter interprets; every other filter is a chart view option sent as-is.
_ADAPTER_FILTERS = {"country", "time", "column"}
# Query parameters the adapter itself sends (not view options).
_OWN_PARAMS = {"v", "csvType", "useColumnShortNames", "tab", "country", "time"}

type JSON = None | bool | int | float | str | list["JSON"] | dict[str, "JSON"]


def _joined(value: str | Sequence[str]) -> str:
    return value if isinstance(value, str) else "~".join(value)


def view_options(filters: Filters) -> dict[str, str]:
    """Chart view options (e.g. `metric`, `source`): every filter the adapter doesn't use."""
    return {k: _joined(v) for k, v in filters.items() if k not in _ADAPTER_FILTERS}


def _params(filters: Filters) -> dict[str, str]:
    params = {
        "v": "1",
        "csvType": "filtered",
        "useColumnShortNames": "true",
        "tab": "chart",  # time series of the selected countries, not the map's snapshot
        **view_options(filters),
    }
    if "country" in filters:
        params["country"] = _joined(filters["country"])
    if "time" in filters:
        params["time"] = _joined(filters["time"])
    return params


def _landed_at(url: httpx.URL, requested: str) -> tuple[str, dict[str, str]]:
    """Chart slug and view options the CSV request ended at (after any redirect)."""
    name = unquote(url.path.rsplit("/", 1)[-1])
    chart = name.removesuffix(".csv") if name.endswith(".csv") else requested
    options = {k: v for k, v in url.params.items() if k not in _OWN_PARAMS}
    return chart, options


def _time_bounds(time: str) -> tuple[str | None, str | None]:
    """OWID `time`: "2015..2023", "earliest..2020", "2015..latest", or one year/date."""
    start, sep, end = time.partition("..")
    if not sep:
        end = start
    return (
        None if start in ("", "earliest") else start,
        None if end in ("", "latest") else end,
    )


def select(obs: list[Observation], filters: Filters) -> list[Observation]:
    """Keep only the requested countries and years, whatever the server sent back.

    Countries match the ISO3 code or, for rows without one, the entity name. Period bounds
    compare on their own length, so a year bound also works for daily charts.
    """
    if "country" in filters:
        value = filters["country"]
        wanted = {value} if isinstance(value, str) else set(value)
        obs = [o for o in obs if o.geo in wanted or o.dims.get("entity") in wanted]
    if "time" in filters:
        start, end = _time_bounds(_joined(filters["time"]))
        obs = [
            o
            for o in obs
            if (start is None or o.period[: len(start)] >= start)
            and (end is None or o.period[: len(end)] <= end)
        ]
    return obs


def parse_csv(raw: bytes, chart: str, column: str | None) -> tuple[str, list[Observation]]:
    """Return the value column used and one Observation per row."""
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise SourceFormatError(f"owid {chart}: not UTF-8 CSV") from exc
    fields = reader.fieldnames or []
    time_col = "year" if "year" in fields else "day" if "day" in fields else None
    if "entity" not in fields or time_col is None:
        raise SourceFormatError(f"owid {chart}: missing entity/year columns ({fields})")
    value_cols = [f for f in fields if f not in _KEY_COLUMNS]
    if column is None:
        if len(value_cols) != 1:
            raise SourceFormatError(f"owid {chart}: pick a column from {value_cols}")
        column = value_cols[0]
    elif column not in value_cols:
        raise SourceNotFound(f"owid {chart}: no column {column!r} in {value_cols}")

    out: list[Observation] = []
    for row in reader:
        cell = (row.get(column) or "").strip()
        try:
            value = float(cell) if cell else None
        except ValueError as exc:
            raise SourceFormatError(f"owid {chart}: non-numeric {cell!r}") from exc
        if value is not None and not math.isfinite(value):
            value = None
        entity = row["entity"]
        code = (row.get("code") or "").strip()
        out.append(
            Observation(
                geo=code or entity,
                period=row[time_col],
                value=value,
                dims={"entity": entity, "column": column},
            )
        )
    return column, out


def _metadata(raw: bytes, column: str) -> tuple[str, str | None, str | None]:
    """Title, unit, citation from `<chart>.metadata.json` (best effort)."""
    try:
        doc = cast(JSON, json.loads(raw))
    except json.JSONDecodeError:
        return "", None, None
    if not isinstance(doc, dict):
        return "", None, None
    chart = doc.get("chart") if isinstance(doc.get("chart"), dict) else {}
    columns = doc.get("columns") if isinstance(doc.get("columns"), dict) else {}
    col = cast(dict[str, JSON], columns).get(column)
    col = col if isinstance(col, dict) else {}
    title = col.get("titleShort") or cast(dict[str, JSON], chart).get("title") or ""
    unit = col.get("unit")
    citation = col.get("citationShort") or cast(dict[str, JSON], chart).get("citation")
    return (
        str(title),
        str(unit) if unit else None,
        str(citation) if citation else None,
    )


class OwidAdapter:
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

    async def _get(self, chart: str, suffix: str, params: dict[str, str]) -> httpx.Response:
        response = await get_with_retries(
            self._client,
            f"{self._base_url}/{chart}.{suffix}",
            source=SOURCE,
            params=params,
            retry_wait=self._retry_wait,
        )
        if response.status_code == 403:
            raise SourceNotRedistributable(f"owid {chart}: data is not redistributable (HTTP 403)")
        if response.status_code == 404:
            raise SourceNotFound(f"owid {chart}: chart not found")
        if response.status_code != 200:
            raise SourceFormatError(f"owid {chart}: unexpected HTTP {response.status_code}")
        return response

    async def fetch_series(self, dataset: str, filters: Filters) -> FetchedSeries:
        """`dataset` is the chart slug; filters: `country` (ISO3, one or many), `time`
        ("2015..2023"), `column` (needed when the chart has several value columns). Any
        other filter is a chart view option, e.g. `energy-mix` with
        {metric: share, source: renewables}."""
        column_filter = filters.get("column")
        csv_response = await self._get(dataset, "csv", _params(filters))
        column, obs = parse_csv(
            csv_response.content,
            dataset,
            column_filter if isinstance(column_filter, str) else None,
        )
        obs = select(obs, filters)
        if not any(o.value is not None for o in obs):
            raise SourceNotFound(f"owid {dataset}: no values for {dict(filters)}")
        chart, options = _landed_at(csv_response.url, dataset)
        meta_response = await self._get(
            chart, "metadata.json", {"v": "1", "useColumnShortNames": "true", **options}
        )
        title, unit, citation = _metadata(meta_response.content, column)
        return FetchedSeries(
            source=SOURCE,
            dataset=dataset,
            url=str(csv_response.request.url),
            retrieved_at=datetime.now(UTC),
            raw_sha256=sha256_hex(csv_response.content),
            observations=obs,
            label=title,
            unit=unit,
            citation=citation or "Our World in Data (CC BY 4.0)",
        )
