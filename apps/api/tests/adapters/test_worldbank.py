"""World Bank adapter against recorded responses, incl. the HTTP-200 error block."""

import hashlib
import json

import httpx
import pytest
from tenacity import wait_none

from holdsup.adapters.base import SourceFormatError, SourceNotFound
from holdsup.adapters.worldbank import WorldBankAdapter, error_message
from tests.adapters.helpers import Handler, fixture, mock_client, serve


def adapter(handler: Handler) -> WorldBankAdapter:
    return WorldBankAdapter(mock_client(handler), retry_wait=wait_none())


async def test_normal_response_two_countries() -> None:
    body = fixture("worldbank/youth_unemployment_it_de.json")
    seen: list[httpx.Request] = []
    series = await adapter(serve(body, seen=seen)).fetch_series(
        "SL.UEM.1524.ZS", {"country": ["IT", "DE"], "date": "2010:2025"}
    )

    values = {(o.geo, o.period): o.value for o in series.observations}
    assert len(values) == 32
    assert values[("IT", "2010")] == 27.91
    assert values[("DE", "2025")] == 6.862
    assert series.observations[0].dims == {"iso3": "DEU", "indicator": "SL.UEM.1524.ZS"}
    assert [o.period for o in series.observations[:2]] == ["2010", "2011"]  # sorted ascending
    assert series.label.startswith("Unemployment, youth total")
    assert series.updated == "2026-10-08"
    assert series.raw_sha256 == hashlib.sha256(body).hexdigest()

    url = seen[0].url
    assert url.path == "/v2/country/IT;DE/indicator/SL.UEM.1524.ZS"
    assert (url.params["format"], url.params["date"], url.params["page"]) == (
        "json",
        "2010:2025",
        "1",
    )


async def test_missing_values_are_kept_as_none() -> None:
    series = await adapter(serve(fixture("worldbank/gini_it_gaps.json"))).fetch_series(
        "SI.POV.GINI", {"country": "IT", "date": "2000:2024"}
    )
    missing = [o.period for o in series.observations if o.value is None]
    assert missing == ["2001", "2024"]
    assert len(series.observations) == 25


async def test_http_200_error_block_is_detected() -> None:
    body = fixture("worldbank/error_invalid_indicator.json")
    with pytest.raises(SourceNotFound, match=r"Invalid value.*id 120"):
        await adapter(serve(body)).fetch_series("NOT.A.CODE", {"country": "IT"})


async def test_unknown_country_returns_empty_data() -> None:
    body = fixture("worldbank/empty_unknown_country.json")
    with pytest.raises(SourceNotFound, match="no values"):
        await adapter(serve(body)).fetch_series("SL.UEM.1524.ZS", {"country": "XX"})


async def test_pages_are_followed_and_hashed_together() -> None:
    rows = json.loads(fixture("worldbank/youth_unemployment_it_de.json"))[1]
    pages = [
        json.dumps([{"page": 1, "pages": 2, "lastupdated": "2026-10-08"}, rows[:20]]).encode(),
        json.dumps([{"page": 2, "pages": 2, "lastupdated": "2026-10-08"}, rows[20:]]).encode(),
    ]
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=pages[int(request.url.params["page"]) - 1])

    series = await adapter(handler).fetch_series("SL.UEM.1524.ZS", {"country": ["IT", "DE"]})

    assert [r.url.params["page"] for r in seen] == ["1", "2"]
    assert len(series.observations) == 32
    assert series.raw_sha256 == hashlib.sha256(pages[0] + pages[1]).hexdigest()


async def test_default_country_is_all() -> None:
    seen: list[httpx.Request] = []
    body = fixture("worldbank/youth_unemployment_it_de.json")
    await adapter(serve(body, seen=seen)).fetch_series("SL.UEM.1524.ZS", {})
    assert seen[0].url.path == "/v2/country/all/indicator/SL.UEM.1524.ZS"
    assert "date" not in seen[0].url.params


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"<html>", "not JSON"),
        (b'{"a": 1}', r"\[meta, data\]"),
        (b'[{"page": 1}, {"x": 1}]', "not a list"),
        (b'[{"page": 1}, [5]]', "not an object"),
        (b'[{"page": 1}, [{"date": "2020"}]]', "country/date"),
        (
            b'[{"page": 1}, [{"country": {"id": "IT"}, "date": "2020", "value": "7"}]]',
            "non-numeric",
        ),
    ],
)
async def test_malformed_bodies(body: bytes, message: str) -> None:
    with pytest.raises(SourceFormatError, match=message):
        await adapter(serve(body)).fetch_series("X", {"country": "IT"})


async def test_non_200_is_not_found() -> None:
    with pytest.raises(SourceNotFound, match="HTTP 400"):
        await adapter(serve(b"", 400)).fetch_series("X", {"country": "IT"})


def test_error_message_variants() -> None:
    assert error_message([{"message": "plain"}]) == "plain"
    assert error_message([{"message": []}]) == "unknown error"
    assert error_message([{"page": 1}, []]) is None
    assert error_message({"message": "not a list body"}) is None
