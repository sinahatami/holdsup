"""Distortion checks in a whole run (P3.4, D026), on the real catalog: the series a check reads
is fetched only when the check applies, joins the receipt's sources, and a flagged check makes
a claim that holds "supported, but framing matters"."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from holdsup.adapters.base import FetchedSeries, Filters, Observation, SourceUnavailable
from holdsup.catalog.index import IndicatorHit
from holdsup.catalog.schema import load_catalog
from holdsup.checks import CheckKind
from holdsup.config import REPO_ROOT
from holdsup.pipeline.prices import PRICE_RATES_ID, real_terms_source
from holdsup.pipeline.result import ClaimResult
from holdsup.pipeline.run import Pipeline
from holdsup.pipeline.trace import StepEvent
from holdsup.router import Router
from holdsup.verdict import Label, load_tolerances
from tests.router.fakes import FakeClient, FakeClock, config, provider
from tests.service.fakes import explain_answer, reply

CATALOG = load_catalog(REPO_ROOT / "packages" / "catalog")
WAGES = CATALOG.get("net_earnings_average_wage")  # euro per year, at current prices
PRICES = CATALOG.get(PRICE_RATES_ID)
TEXT = "Net earnings in Italy rose 5% between 2015 and 2020."
EARNINGS_IT = {"2015": 30000, "2016": 30300, "2017": 30600, "2018": 30900, "2019": 31200,
               "2020": 31500}  # fmt: skip


@dataclass
class ByDataset:
    """Rows per dataset code; a dataset not listed is down."""

    rows: dict[str, list[Observation]]
    calls: list[str] = field(default_factory=list)

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls.append(dataset)
        if dataset not in self.rows:
            raise SourceUnavailable(f"{dataset} is down")
        return FetchedSeries(
            source=source, dataset=dataset, url=f"https://example.invalid/{dataset}",
            retrieved_at=datetime(2026, 11, 12, tzinfo=UTC), raw_sha256="cd" * 32,
            observations=self.rows[dataset],
        )  # fmt: skip


async def search(phrase: str, k: int) -> list[IndicatorHit]:
    ordered = [WAGES, *(s for s in CATALOG.indicators if s.id != WAGES.id)]
    return [
        IndicatorHit(id=s.id, name=s.name, source=str(s.source), source_code=s.source_code,
                     unit=s.unit, frequency=str(s.frequency), definition=s.definition,
                     score=1 - i / 100)
        for i, s in enumerate(ordered[:k])
    ]  # fmt: skip


def wage_claim() -> dict[str, Any]:
    return {
        "quote": TEXT[:-1], "indicator_phrase": "net earnings", "geo": "IT", "geo_named": True,
        "peers": [], "start": "2015", "start_named": True, "end": "2020", "lookback": None,
        "office": None,
        "assertion": {"type": "percent", "value": 5, "direction": "up", "unit": "%",
                      "start_value": None, "end_value": None},
    }  # fmt: skip


MATCH = {"indicator_id": WAGES.id, "confidence": "high", "reason": "Same.", "alternatives": []}
CHANGE = {"op": "change", "geo": "IT", "start": "2015", "end": "2020", "kind": "percent"}
SCRIPT = [
    reply({"speaker": None, "said_on": None, "claims": [wage_claim()]}),
    reply(MATCH),
    reply({"calls": [CHANGE], "answer": [0], "reason": "A change in percent."}),
    explain_answer(
        "Net earnings rose 5% from 30,000 in 2015 to 31,500 in 2020; 27,172 in 2015 prices."
    ),
]


async def run(inflation: float | None) -> tuple[ClaimResult, ByDataset]:
    rows = {WAGES.source_code: [Observation("IT", p, v) for p, v in EARNINGS_IT.items()]}
    if inflation is not None:
        rows[PRICES.source_code] = [
            Observation("ITA", str(y), inflation) for y in range(2010, 2021)
        ]
    fetcher = ByDataset(rows)
    client = FakeClient()
    client.script("fake", SCRIPT)
    steps = {s: ["fake"] for s in ("extract", "match", "plan", "explain")}
    pipeline = Pipeline(
        router=Router(config(provider("fake"), steps=steps), client, clock=FakeClock()),
        catalog=CATALOG,
        search=search,
        fetcher=fetcher,
        tolerances=load_tolerances(),
        today=lambda: date(2026, 11, 12),
    )

    async def emit(_: StepEvent) -> None:
        return None

    out = await pipeline.run(TEXT, emit)
    return out.claims[0], fetcher


async def test_a_pay_rise_below_inflation_holds_but_the_framing_matters() -> None:
    c, fetcher = await run(inflation=3.0)
    assert fetcher.calls == [WAGES.source_code, PRICES.source_code]
    [real] = [ch for ch in c.distortion_checks if ch.kind is CheckKind.REAL]
    assert real.flagged and real.uses == PRICE_RATES_ID
    assert real.text == (
        "after inflation it fell: 30,000 in 2015, 27,172 in 2020 (euro per year, 2015 prices)"
    )
    assert c.verdict.label is Label.SUPPORTED_FRAMING_MATTERS
    assert c.verdict.reason.endswith(f"but {real.text}.")
    assert [s.indicator.id for s in c.extra_sources] == [PRICE_RATES_ID]
    # The explanation may quote the check's numbers: they are computed results.
    assert c.explanation_source == "model"


async def test_a_pay_rise_above_inflation_stays_supported() -> None:
    c, _ = await run(inflation=0.5)
    [real] = [ch for ch in c.distortion_checks if ch.kind is CheckKind.REAL]
    assert not real.flagged and real.text.startswith("after inflation it also rose")
    assert c.verdict.label is Label.SUPPORTED


NEET = CATALOG.get("neet_rate")  # annual, % of the age group


async def run_neet(stated: float, kind: str) -> ClaimResult:
    """The same rate (24.4 in 2016, 16.1 in 2023: down 8.3 points, or 34% in percent) with the
    claim stating `stated` as a change of `kind`. The number is in the text: the extractor drops
    one that is not."""
    text = f"Italy's NEET rate fell {stated:g}% between 2016 and 2023."
    claim = {
        "quote": text[:-1], "indicator_phrase": "NEET rate", "geo": "IT", "geo_named": True,
        "peers": [], "start": "2016", "start_named": True, "end": "2023", "lookback": None,
        "office": None,
        "assertion": {"type": kind, "value": stated, "direction": "down", "unit": "%",
                      "start_value": None, "end_value": None},
    }  # fmt: skip
    change = {"op": "change", "geo": "IT", "start": "2016", "end": "2023", "kind": kind}
    script = [
        reply({"speaker": None, "said_on": None, "claims": [claim]}),
        reply({"indicator_id": NEET.id, "confidence": "high", "reason": "Same.",
               "alternatives": []}),
        reply({"calls": [change], "answer": [0], "reason": f"A change in {kind}."}),
        explain_answer("The rate fell from 24.4% in 2016 to 16.1% in 2023."),
    ]  # fmt: skip
    rows = {NEET.source_code: [Observation("IT", "2016", 24.4), Observation("IT", "2023", 16.1)]}
    client = FakeClient()
    client.script("fake", script)
    steps = {s: ["fake"] for s in ("extract", "match", "plan", "explain")}

    async def neet_search(phrase: str, k: int) -> list[IndicatorHit]:
        return [IndicatorHit(id=NEET.id, name=NEET.name, source=str(NEET.source),
                             source_code=NEET.source_code, unit=NEET.unit,
                             frequency=str(NEET.frequency), definition=NEET.definition,
                             score=1.0)]  # fmt: skip

    pipeline = Pipeline(
        router=Router(config(provider("fake"), steps=steps), client, clock=FakeClock()),
        catalog=CATALOG,
        search=neet_search,
        fetcher=ByDataset(rows),
        tolerances=load_tolerances(),
        today=lambda: date(2026, 11, 12),
    )

    async def emit(_: StepEvent) -> None:
        return None

    return (await pipeline.run(text, emit)).claims[0]


async def test_points_stated_as_a_percent_hold_but_the_framing_matters() -> None:
    """A rate that fell 8.3 points (34% in percent), said to have fallen 8.3%: the number is
    right as points, so the claim is not "not supported"; it blurs points and percent."""
    c = await run_neet(8.3, "percent")
    [points] = [ch for ch in c.distortion_checks if ch.kind is CheckKind.POINTS]
    assert points.flagged
    assert c.verdict.label is Label.SUPPORTED_FRAMING_MATTERS
    assert c.verdict.reason.endswith(f"but {points.text}.")
    assert all(p.holds for p in c.verdict.parts)


async def test_a_number_wrong_as_percent_and_as_points_is_still_not_supported() -> None:
    c = await run_neet(5.0, "percent")
    [points] = [ch for ch in c.distortion_checks if ch.kind is CheckKind.POINTS]
    assert not points.flagged
    assert c.verdict.label is Label.NOT_SUPPORTED


async def test_percent_stated_right_as_percent_stays_supported() -> None:
    c = await run_neet(34, "percent")
    assert c.verdict.label is Label.SUPPORTED


async def test_no_prices_leaves_the_check_out_and_the_claim_checked() -> None:
    c, fetcher = await run(inflation=None)
    assert fetcher.calls == [WAGES.source_code, PRICES.source_code]
    assert CheckKind.REAL not in {ch.kind for ch in c.distortion_checks}
    assert c.extra_sources == [] and c.verdict.label is Label.SUPPORTED


def test_the_real_terms_source() -> None:
    gdp, debt = CATALOG.get("nominal_gdp_eur"), CATALOG.get("government_debt_eur")
    real = real_terms_source(CATALOG, gdp, "IT")
    assert real is not None and real.id == "real_gdp_volume"
    assert real_terms_source(CATALOG, gdp, "US") is None  # not covered
    prices = real_terms_source(CATALOG, debt, "IT")
    assert prices is not None and prices.id == PRICE_RATES_ID
    assert real_terms_source(CATALOG, debt, "EU") is None  # national prices only
    assert real_terms_source(CATALOG, CATALOG.get("minimum_wage_eur"), "DE") is None
    assert real_terms_source(CATALOG, CATALOG.get("unemployment_rate_ilo"), "IT") is None
