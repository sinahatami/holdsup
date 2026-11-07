"""Our World in Data adapter against recorded responses, incl. 403 (not redistributable)."""

import hashlib

import httpx
import pytest
from tenacity import wait_none

from holdsup.adapters.base import (
    Observation,
    SourceFormatError,
    SourceNotFound,
    SourceNotRedistributable,
)
from holdsup.adapters.owid import OwidAdapter, parse_csv, select
from tests.adapters.helpers import Handler, fixture, mock_client

CSV = fixture("owid/co2_per_capita_it_de.csv")
META = fixture("owid/co2_per_capita.metadata.json")


def adapter(handler: Handler) -> OwidAdapter:
    return OwidAdapter(mock_client(handler), retry_wait=wait_none())


def chart_server(
    csv_body: bytes, meta_body: bytes = META, seen: list[httpx.Request] | None = None
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if request.url.path.endswith(".metadata.json"):
            return httpx.Response(200, content=meta_body)
        return httpx.Response(200, content=csv_body, headers={"content-type": "text/csv"})

    return handler


async def test_csv_and_metadata() -> None:
    seen: list[httpx.Request] = []
    series = await adapter(chart_server(CSV, seen=seen)).fetch_series(
        "co2-emissions-per-capita", {"country": ["ITA", "DEU"], "time": "2015..2023"}
    )

    values = {(o.geo, o.period): o.value for o in series.observations}
    assert len(values) == 18
    assert values[("ITA", "2015")] == 5.9635468
    assert values[("DEU", "2023")] == 7.022808
    assert series.observations[0].dims == {
        "entity": "Germany",
        "column": "emissions_total_per_capita",
    }
    assert series.unit == "tonnes per person"
    assert series.citation is not None and series.citation.startswith("Global Carbon Budget")
    assert series.label == "CO₂ emissions per capita"
    assert series.raw_sha256 == hashlib.sha256(CSV).hexdigest()

    csv_request = seen[0]
    assert csv_request.url.path == "/grapher/co2-emissions-per-capita.csv"
    assert csv_request.url.params["country"] == "ITA~DEU"
    assert csv_request.url.params["time"] == "2015..2023"
    assert seen[1].url.path == "/grapher/co2-emissions-per-capita.metadata.json"


async def test_entities_without_iso_code_use_the_entity_name() -> None:
    series = await adapter(
        chart_server(fixture("owid/natural_gas_prices.csv"), b"{}")
    ).fetch_series("natural-gas-prices", {})
    assert {o.geo for o in series.observations} >= {"Netherlands TTF", "US Henry Hub"}
    assert series.unit is None
    assert series.citation == "Our World in Data (CC BY 4.0)"


async def test_403_raises_not_redistributable_without_retrying() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, content=fixture("owid/error_403_not_redistributable.txt"))

    with pytest.raises(SourceNotRedistributable, match="not redistributable"):
        await adapter(handler).fetch_series("some-licensed-chart", {})
    assert calls == 1


async def test_404_is_not_found() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=fixture("owid/error_not_found.csv"))

    with pytest.raises(SourceNotFound, match="chart not found"):
        await adapter(handler).fetch_series("no-such-chart-holdsup", {})


async def test_unexpected_status_is_format_error() -> None:
    with pytest.raises(SourceFormatError, match="HTTP 302"):
        await adapter(lambda _: httpx.Response(302)).fetch_series("x", {})


async def test_all_empty_values_is_not_found() -> None:
    body = b"entity,code,year,v\nItaly,ITA,2020,\n"
    with pytest.raises(SourceNotFound, match="no values"):
        await adapter(chart_server(body)).fetch_series("x", {"country": "ITA"})


async def test_unparseable_metadata_is_tolerated() -> None:
    series = await adapter(chart_server(CSV, b"not json")).fetch_series("co2", {})
    assert (series.label, series.unit) == ("", None)
    series = await adapter(chart_server(CSV, b"[1]")).fetch_series("co2", {})
    assert series.label == ""


def test_multiple_value_columns_need_a_column_filter() -> None:
    body = b"entity,code,year,coal,gas\nItaly,ITA,2020,1.5,2.5\n"
    with pytest.raises(SourceFormatError, match="pick a column"):
        parse_csv(body, "mix", None)
    column, obs = parse_csv(body, "mix", "gas")
    assert (column, obs[0].value) == ("gas", 2.5)
    with pytest.raises(SourceNotFound, match="no column 'oil'"):
        parse_csv(body, "mix", "oil")


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"\xff\xfe\x00", "UTF-8"),
        (b"country,year,v\nItaly,2020,1\n", "entity/year"),
        (b"entity,year,v\nItaly,2020,abc\n", "non-numeric"),
    ],
)
def test_malformed_csv(body: bytes, message: str) -> None:
    with pytest.raises(SourceFormatError, match=message):
        parse_csv(body, "x", None)


def test_daily_charts_and_non_finite_values() -> None:
    _, obs = parse_csv(b"entity,code,day,v\nItaly,ITA,2020-03-01,inf\n", "x", None)
    assert (obs[0].period, obs[0].value) == ("2020-03-01", None)


# --- multi-view charts, redirects, and filters the server ignores ----------------------------

MIX_CSV = fixture("owid/energy_mix_renewables_share_de_it.csv")
MIX_META = fixture("owid/energy_mix_renewables_share.metadata.json")
MIX_SNAPSHOT = fixture("owid/energy_mix_renewables_share_map_snapshot.csv")
# Live behaviour on 2026-11-07: the old slug 301s to the energy-mix view, keeping the query,
# and the old slug's metadata URL is a 404.
REDIRECT = "/grapher/energy-mix.csv?metric=share&source=renewables&"


def energy_mix_server(seen: list[httpx.Request], csv_body: bytes = MIX_CSV) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == "/grapher/renewable-share-energy.csv":
            query = request.url.query.decode()
            return httpx.Response(301, headers={"location": REDIRECT + query})
        if path == "/grapher/energy-mix.csv":
            return httpx.Response(200, content=csv_body, headers={"content-type": "text/csv"})
        if path == "/grapher/energy-mix.metadata.json":
            return httpx.Response(200, content=MIX_META)
        return httpx.Response(404, content=b"Not found")

    return handler


async def test_view_options_are_sent_and_metadata_matches_the_view() -> None:
    seen: list[httpx.Request] = []
    filters = {
        "metric": "share",
        "source": "renewables",
        "column": "renewables_share_pct",
        "country": ["DEU", "ITA"],
        "time": "2015..2024",
    }
    series = await adapter(energy_mix_server(seen)).fetch_series("energy-mix", filters)

    values = {(o.geo, o.period): o.value for o in series.observations}
    assert len(values) == 20
    assert values[("DEU", "2024")] == 15.078017
    assert values[("ITA", "2015")] == 12.642635
    assert series.label == "Renewables as a share of total energy supply"
    assert series.unit == "%"
    assert series.citation is not None and series.citation.startswith("Energy Institute")

    csv_params = seen[0].url.params
    assert (csv_params["metric"], csv_params["source"], csv_params["tab"]) == (
        "share",
        "renewables",
        "chart",
    )
    assert "column" not in csv_params  # used by the adapter, not sent
    meta_params = seen[1].url.params
    assert (meta_params["metric"], meta_params["source"]) == ("share", "renewables")
    assert "country" not in meta_params and "tab" not in meta_params


async def test_old_slug_follows_the_redirect_for_csv_and_metadata() -> None:
    seen: list[httpx.Request] = []
    series = await adapter(energy_mix_server(seen)).fetch_series(
        "renewable-share-energy", {"column": "renewables_share_pct", "country": "DEU"}
    )

    assert [r.url.path for r in seen] == [
        "/grapher/renewable-share-energy.csv",
        "/grapher/energy-mix.csv",
        "/grapher/energy-mix.metadata.json",  # the old slug's metadata URL would 404
    ]
    assert {o.geo for o in series.observations} == {"DEU"}
    assert series.dataset == "renewable-share-energy"  # what the catalog asked for
    assert series.url.startswith("https://ourworldindata.org/grapher/energy-mix.csv?")
    assert series.unit == "%"
    assert series.raw_sha256 == hashlib.sha256(MIX_CSV).hexdigest()


async def test_a_server_ignoring_country_and_time_cannot_leak_other_rows() -> None:
    # The map snapshot: every country, only the first and last year of the range.
    seen: list[httpx.Request] = []
    filters = {"metric": "share", "source": "renewables", "country": ["DEU", "ITA"]}
    series = await adapter(energy_mix_server(seen, MIX_SNAPSHOT)).fetch_series(
        "energy-mix", {**filters, "time": "2015..2024"}
    )
    assert {(o.geo, o.period) for o in series.observations} == {
        ("DEU", "2015"),
        ("DEU", "2024"),
        ("ITA", "2015"),
        ("ITA", "2024"),
    }

    with pytest.raises(SourceNotFound, match="no values"):
        await adapter(energy_mix_server(seen, MIX_SNAPSHOT)).fetch_series(
            "energy-mix", {**filters, "time": "2016..2023"}
        )


def _obs(geo: str, period: str, entity: str = "") -> Observation:
    return Observation(geo=geo, period=period, value=1.0, dims={"entity": entity or geo})


@pytest.mark.parametrize(
    ("time", "kept"),
    [
        ("2019..2020", ["2019", "2020-06-01"]),
        ("earliest..2019", ["2018", "2019"]),
        ("2020..latest", ["2020-06-01", "2021"]),
        ("2019", ["2019"]),
        ("2020-01-01..2020-12-31", ["2020-06-01"]),
    ],
)
def test_select_time_bounds(time: str, kept: list[str]) -> None:
    obs = [_obs("ITA", p) for p in ("2018", "2019", "2020-06-01", "2021")]
    assert [o.period for o in select(obs, {"time": time})] == kept


def test_select_countries_by_code_or_entity_name() -> None:
    obs = [_obs("ITA", "2020", "Italy"), _obs("US Henry Hub", "2020"), _obs("DEU", "2020")]
    picked = select(obs, {"country": ["ITA", "US Henry Hub"]})
    assert [o.geo for o in picked] == ["ITA", "US Henry Hub"]
    assert [o.geo for o in select(obs, {"country": "Germany"})] == []
    assert select(obs, {}) == obs
