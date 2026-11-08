"""Eurostat adapter against recorded responses (httpx.MockTransport; no network)."""

import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from tenacity import wait_none

from holdsup.adapters.base import SourceFormatError, SourceNotFound, SourceUnavailable
from holdsup.adapters.eurostat import BASE_URL, EurostatAdapter, build_params
from holdsup.ops import ChangeKind, Frequency, Series, change, parse_period

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "eurostat"
Handler = Callable[[httpx.Request], httpx.Response]


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def adapter(handler: Handler) -> EurostatAdapter:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return EurostatAdapter(client, retry_wait=wait_none())


def serve(body: bytes, status: int = 200, seen: list[httpx.Request] | None = None) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    return handler


async def test_fetch_series_decodes_and_hashes_raw_response() -> None:
    body = fixture("une_rt_a_annual.json")
    seen: list[httpx.Request] = []
    filters = {"geo": ["IT", "DE", "FR"], "sex": "T", "age": "Y15-74", "unit": "PC_ACT"}

    series = await adapter(serve(body, seen=seen)).fetch_series("une_rt_a", filters)

    assert series.source == "eurostat"
    assert series.dataset == "une_rt_a"
    assert series.raw_sha256 == hashlib.sha256(body).hexdigest()
    assert len(series.observations) == 36
    assert series.dimension_labels["geo"]["DE"] == "Germany"
    assert series.updated is not None
    assert series.retrieved_at.tzinfo is not None

    request = seen[0]
    assert str(request.url).startswith(f"{BASE_URL}/une_rt_a?")
    assert request.url.params.get_list("geo") == ["IT", "DE", "FR"]
    assert request.url.params["format"] == "JSON"
    assert series.url == str(request.url)


async def test_half_yearly_periods_are_kept_as_the_source_writes_them() -> None:
    """Eurostat writes a half-year as 2023-S1; the adapter passes it on, and a Series reads it."""
    filters = {"geo": ["DE", "FR", "BG"], "currency": "EUR"}
    fetched = await adapter(serve(fixture("earn_mw_cur_semiannual.json"))).fetch_series(
        "earn_mw_cur", filters
    )
    periods = {o.period for o in fetched.observations}
    assert periods == {f"{y}-S{h}" for y in range(2022, 2027) for h in (1, 2)}
    assert fetched.dimension_labels["freq"] == {"S": "Half-yearly, semesterly"}

    de = Series.from_observations(fetched.observations, "DE", "euro per month")
    assert de.frequency is Frequency.SEMIANNUAL
    assert (str(de.first), str(de.last)) == ("2022-S1", "2026-S2")
    assert [de.get(parse_period(p)) for p in ("2022-S1", "2022-S2", "2023-S1")] == [
        1_634.0, 1_739.0, 1_997.0,
    ]  # fmt: skip
    changed = change(de, "2022-S1", "2023-S1", ChangeKind.ABSOLUTE)
    assert changed.value == 363.0


def test_build_params_repeats_list_values_and_sorts_keys() -> None:
    assert build_params({"unit": "PC_ACT", "geo": ["IT", "DE"]}) == {
        "format": ["JSON"],
        "lang": ["EN"],
        "geo": ["IT", "DE"],
        "unit": ["PC_ACT"],
    }


async def test_404_is_source_not_found_with_eurostat_label() -> None:
    with pytest.raises(SourceNotFound, match="NO_SUCH_DATASET"):
        await adapter(serve(fixture("error_not_found.json"), 404)).fetch_series(
            "no_such_dataset", {}
        )


async def test_400_with_unreadable_body_is_source_not_found() -> None:
    with pytest.raises(SourceNotFound, match="bad filter"):
        await adapter(serve(b"bad filter", 400)).fetch_series("une_rt_a", {"geo": "XX"})


async def test_all_cells_missing_is_source_not_found() -> None:
    body = (
        b'{"class":"dataset","id":["geo","time"],"size":[1,1],"value":{},'
        b'"dimension":{"geo":{"category":{"index":["IT"]}},"time":{"category":{"index":["2020"]}}}}'
    )
    with pytest.raises(SourceNotFound, match="no values"):
        await adapter(serve(body)).fetch_series("une_rt_a", {"geo": "IT"})


async def test_unexpected_status_is_format_error() -> None:
    with pytest.raises(SourceFormatError, match="HTTP 302"):
        await adapter(serve(b"", 302)).fetch_series("une_rt_a", {})


async def test_5xx_is_retried_then_succeeds() -> None:
    responses = iter([503, 502, 200])
    body = fixture("une_rt_m_youth_monthly.json")
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        status = next(responses)
        return httpx.Response(status, content=body if status == 200 else b"busy")

    series = await adapter(handler).fetch_series("une_rt_m", {"geo": "IT"})
    assert calls == 3
    assert len(series.observations) == 66


async def test_persistent_5xx_or_429_is_source_unavailable() -> None:
    for status in (500, 429):
        with pytest.raises(SourceUnavailable, match=f"HTTP {status}"):
            await adapter(serve(b"", status)).fetch_series("une_rt_a", {})


async def test_transport_errors_are_retried_then_unavailable() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(SourceUnavailable, match="timed out"):
        await adapter(handler).fetch_series("une_rt_a", {})
    assert calls == 3
