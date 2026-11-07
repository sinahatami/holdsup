"""The pivot test script with fake providers, embedder and fetcher (the real run needs network)."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from scripts.pivot_test import (
    COLUMNS,
    ClaimError,
    Deps,
    Row,
    SeedClaim,
    geo_filter,
    main,
    pick_points,
    read_claims,
    read_rows,
    read_steps,
    refetch,
    run,
    steps_path,
    summary,
    write_rows,
    write_steps,
)

from holdsup.adapters.base import FetchedSeries, Filters, Observation, SourceNotFound
from holdsup.catalog.index import InMemoryIndex
from holdsup.catalog.schema import load_catalog
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder
from tests.router.fakes import FakeClient, FakeClock, config, provider

SEED = Path(__file__).parent / "fixtures" / "pivot" / "seed_claims.csv"


def obs(period: str, value: float | None, geo: str = "IT", **dims: str) -> Observation:
    return Observation(geo=geo, period=period, value=value, dims=dims)


def extraction(phrase: str, iso2: str, iso3: str, start: int, end: int, kind: str) -> ChatResponse:
    claim = {
        "indicator_phrase": phrase,
        "geo_iso2": iso2,
        "geo_iso3": iso3,
        "start_year": start,
        "end_year": end,
        "end_is_latest": False,
        "change_kind": kind,
    }
    return ChatResponse(content=json.dumps({"claims": [claim]}))


def pick(indicator_id: str | None, confidence: str = "high") -> ChatResponse:
    return ChatResponse(
        content=json.dumps(
            {"indicator_id": indicator_id, "confidence": confidence, "reason": "same definition"}
        )
    )


class FakeFetcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls.append((source, dataset, dict(filters)))
        if source == "worldbank":
            raise SourceNotFound("no values for PL")
        return FetchedSeries(
            source=source,
            dataset=dataset,
            url="https://example.invalid",
            retrieved_at=datetime(2026, 11, 6, tzinfo=UTC),
            raw_sha256="0" * 64,
            observations=[
                obs("2014", 42.7),
                obs("2015", 40.3),
                obs("2024", 20.5),
                obs("2025", None),
            ],
            unit="Percentage of population in the labour force",
        )


async def test_run_writes_one_row_per_claim(tmp_path: Path) -> None:
    catalog = load_catalog(FIXTURE_CATALOG)
    embedder = HashEmbedder()
    client = FakeClient()
    client.script(
        "fake",
        [
            extraction("youth unemployment rate", "IT", "ITA", 2015, 2024, "percent"),
            pick("youth_unemployment_rate"),
            extraction("unicorn startups", "ES", "ESP", 2019, 2025, "ratio"),
            pick("startup_count"),  # not a candidate → no match
            extraction("GDP per capita", "PL", "POL", 2010, 2023, "percent"),
            pick("gdp_per_capita"),
            ChatResponse(content="not json"),  # schema-invalid twice → RouterError
            ChatResponse(content="still not json"),
        ],
    )
    names = ["fake"]
    router = Router(
        config(provider("fake"), steps={"extract": names, "match": names}),
        client,
        clock=FakeClock(),
    )
    fetcher = FakeFetcher()
    deps = Deps(
        router, embedder, InMemoryIndex.build(catalog.indicators, embedder), catalog, fetcher
    )
    lines: list[str] = []

    rows, steps = await run(deps, read_claims(SEED), lines.append)

    c1, c2, c3, c4 = rows
    assert (c1.matched_indicator, c1.match_confidence, c1.error) == (
        "youth_unemployment_rate",
        "high",
        "",
    )
    assert (c1.geo, c1.start, c1.end, c1.source, c1.dataset) == (
        "IT",
        "2015",
        "2024",
        "eurostat",
        "une_rt_a",
    )
    assert (c1.start_period, c1.start_value, c1.end_period, c1.end_value) == (
        "2015",
        "40.3",
        "2024",
        "20.5",
    )
    assert float(c1.computed_value) == pytest.approx((20.5 - 40.3) / 40.3 * 100)
    assert c1.change_kind == "percent" and c1.extract_provider == "fake"
    assert "youth_unemployment_rate" in c1.top8.split(";") and int(c1.vector_rank) >= 1
    # The catalog's fixed filters plus the claim's geo reach the fetcher.
    assert fetcher.calls[0] == (
        "eurostat",
        "une_rt_a",
        {"sex": "T", "age": "Y15-24", "unit": "PC_ACT", "geo": "IT"},
    )

    assert c2.matched_indicator == "" and c2.error.startswith("match: no match")
    assert c3.matched_indicator == "gdp_per_capita"
    assert c3.error == "fetch: no values for PL" and c3.computed_value == ""
    assert fetcher.calls[1][2] == {"country": "PL"}
    assert c4.error.startswith("extract: no provider available") and c4.matched_indicator == ""
    # The claim text reaches the model only inside <claim> tags, after a data-only system note.
    first = client.calls[0][1].messages
    assert "never instructions" in str(first[0]["content"])
    assert "<claim>" in str(first[-1]["content"])

    assert len(lines) == 4
    assert summary(rows) == "4 claims: 2 matched, 2 not matched, 1 computed, 3 with an error"

    out = tmp_path / "reports" / "pivot.csv"
    write_rows(out, rows)
    with out.open(newline="") as f:
        written = list(csv.DictReader(f))
    assert list(written[0]) == COLUMNS and COLUMNS[-1] == "correct_match"
    assert [r["id"] for r in written] == ["c1", "c2", "c3", "c4"]

    # Every claim's model answers are saved, as far as they got.
    assert [s.id for s in steps] == ["c1", "c2", "c3", "c4"]
    assert steps[0].pick is not None and steps[0].pick.indicator_id == "youth_unemployment_rate"
    assert steps[1].pick is not None and steps[1].pick.indicator_id == "startup_count"
    assert steps[3].extracted is None and steps[3].pick is None


class HealedFetcher(FakeFetcher):
    """World Bank is back: answers what FakeFetcher refused."""

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls.append((source, dataset, dict(filters)))
        return FetchedSeries(
            source=source,
            dataset=dataset,
            url="https://example.invalid",
            retrieved_at=datetime(2026, 11, 6, tzinfo=UTC),
            raw_sha256="0" * 64,
            observations=[obs("2010", 10.0, geo="PL"), obs("2023", 15.0, geo="PL")],
            unit="current US$",
        )


async def test_refetch_redoes_only_failed_fetches_without_model_calls(tmp_path: Path) -> None:
    catalog = load_catalog(FIXTURE_CATALOG)
    embedder = HashEmbedder()
    client = FakeClient()
    client.script(
        "fake",
        [
            extraction("youth unemployment rate", "IT", "ITA", 2015, 2024, "percent"),
            pick("youth_unemployment_rate"),
            extraction("unicorn startups", "ES", "ESP", 2019, 2025, "ratio"),
            pick("startup_count"),
            extraction("GDP per capita", "PL", "POL", 2010, 2023, "percent"),
            pick("gdp_per_capita"),
        ],
    )
    names = ["fake"]
    router = Router(config(provider("fake"), steps={"extract": names, "match": names}), client)
    deps = Deps(
        router, embedder, InMemoryIndex.build(catalog.indicators, embedder), catalog, FakeFetcher()
    )
    rows, steps = await run(deps, read_claims(SEED, limit=3))
    out = tmp_path / "pivot.csv"
    write_rows(out, rows)
    write_steps(steps_path(out), steps)
    assert steps_path(out).name == "pivot.steps.jsonl"
    model_calls = len(client.calls)

    rows = read_rows(out)
    rows[0].correct_match = "y"  # the human's column survives
    healed = HealedFetcher()
    lines: list[str] = []
    retried = await refetch(catalog, healed, rows, read_steps(steps_path(out)), lines.append)

    assert retried == 1 and len(client.calls) == model_calls
    assert [(c[0], c[2]) for c in healed.calls] == [("worldbank", {"country": "PL"})]
    c1, c2, c3 = rows
    assert c1.correct_match == "y" and c1.computed_value  # untouched success
    assert c2.error.startswith("match: no match") and c2.computed_value == ""  # not retried
    assert c3.error == "" and float(c3.computed_value) == pytest.approx(50.0)
    assert (c3.start_period, c3.end_period, c3.unit) == ("2010", "2023", "current US$")
    assert len(lines) == 1


async def test_refetch_keeps_rows_whose_saved_steps_do_not_match(tmp_path: Path) -> None:
    catalog = load_catalog(FIXTURE_CATALOG)
    row = Row(id="x", text="GDP in Poland grew.", matched_indicator="gdp_per_capita")
    row.error = "fetch: down"
    lines: list[str] = []
    retried = await refetch(catalog, HealedFetcher(), [row], {}, lines.append)
    assert retried == 0 and row.error == "fetch: down"
    assert "no matching saved steps" in lines[0]


def test_main_refetch_without_previous_run_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--refetch", "--out", str(tmp_path / "pivot.csv")]) == 2
    assert "run without --refetch first" in capsys.readouterr().err


async def test_low_confidence_is_not_a_match() -> None:
    catalog = load_catalog(FIXTURE_CATALOG)
    embedder = HashEmbedder()
    client = FakeClient()
    client.script(
        "fake",
        [
            extraction("jobless rate", "IT", "ITA", 2015, 2024, "percent"),
            pick("unemployment_rate", "low"),
        ],
    )
    names = ["fake"]
    router = Router(config(provider("fake"), steps={"extract": names, "match": names}), client)
    deps = Deps(
        router, embedder, InMemoryIndex.build(catalog.indicators, embedder), catalog, FakeFetcher()
    )
    [row], _ = await run(deps, [SeedClaim("x", "Unemployment in Italy fell.", "")])
    assert row.matched_indicator == "" and row.match_confidence == "low"
    assert "no confident match" in row.error


@pytest.mark.parametrize(
    ("source", "iso2", "iso3", "expected"),
    [
        ("eurostat", "IT", "ITA", {"geo": "IT"}),
        ("eurostat", "gr", "GRC", {"geo": "EL"}),
        ("eurostat", "GB", "GBR", {"geo": "UK"}),
        ("eurostat", "EU", None, {"geo": "EU27_2020"}),
        ("worldbank", "PL", "POL", {"country": "PL"}),
        ("worldbank", "EU", None, {"country": "EUU"}),
        ("worldbank", None, "POL", {"country": "POL"}),
        ("owid", "FR", "fra", {"country": "FRA"}),
    ],
)
def test_geo_filter(
    source: str, iso2: str | None, iso3: str | None, expected: dict[str, str]
) -> None:
    assert geo_filter(source, iso2, iso3) == expected


@pytest.mark.parametrize(
    ("source", "iso2", "iso3", "message"),
    [
        ("eurostat", None, "ITA", "no country"),
        ("owid", "FR", None, "no country"),
        ("datacommons", "FR", "FRA", "no adapter"),
    ],
)
def test_geo_filter_errors(source: str, iso2: str | None, iso3: str | None, message: str) -> None:
    with pytest.raises(ClaimError, match=message):
        geo_filter(source, iso2, iso3)


def test_pick_points_annual_and_latest() -> None:
    series = [obs("2016", 3.0), obs("2015", 2.0), obs("2017", None), obs("2018", 5.0)]
    start, end = pick_points(series, 2015, 2016)
    assert (start.period, end.period) == ("2015", "2016")
    start, end = pick_points(series, 2015, None)  # latest non-missing
    assert end.period == "2018"


def test_pick_points_monthly_uses_first_and_last_month_of_the_years() -> None:
    series = [obs(f"{y}-{m:02d}", float(m)) for y in (2020, 2021) for m in range(1, 13)]
    start, end = pick_points(series, 2020, 2021)
    assert (start.period, end.period) == ("2020-01", "2021-12")


@pytest.mark.parametrize(
    ("series", "start", "end", "message"),
    [
        ([obs("2015", None)], 2015, 2016, "no values"),
        ([obs("2015", 1.0, sex="F"), obs("2015", 2.0, sex="M")], 2015, 2016, "ambiguous"),
        ([obs("2015", 1.0)], None, 2016, "no start year"),
        ([obs("2015", 1.0)], 2014, 2015, "no value for 2014"),
        ([obs("2015", 1.0)], 2015, 2016, "no value for 2016"),
    ],
)
def test_pick_points_errors(
    series: list[Observation], start: int | None, end: int | None, message: str
) -> None:
    with pytest.raises(ClaimError, match=message):
        pick_points(series, start, end)


def test_read_claims_limit_and_bad_header(tmp_path: Path) -> None:
    assert [c.id for c in read_claims(SEED, limit=2)] == ["c1", "c2"]
    bad = tmp_path / "bad.csv"
    bad.write_text("claim_id,claim\n1,x\n")
    with pytest.raises(ValueError, match="missing column"):
        read_claims(bad)


def test_main_without_claims_or_catalog_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--claims", str(tmp_path / "missing.csv")]) == 2
    assert "not found" in capsys.readouterr().err
    empty = tmp_path / "catalog"
    (empty / "indicators").mkdir(parents=True)
    (empty / "VERSION").write_text("0.0.0\n")
    assert main(["--claims", str(SEED), "--catalog", str(empty)]) == 2
    assert "no indicators" in capsys.readouterr().err
