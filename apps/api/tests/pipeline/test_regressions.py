"""Regression tests for claims that came out wrong in live runs (2026-11-07).

Recorded source data (tests/fixtures/series, `make record-series`), the real catalog, and
scripted model replies that reproduce what the models answered live. Each test says what went
wrong. The same claims are in eval/smoke_claims.jsonl.

First run:
- r001 "fell from 11.9% in 2015 to 7.7% in 2023": the plan compared 2015-01 with 2023-12.
- c004 "In 2011 ... 29%": the monthly youth series was turned down for being monthly;
  "today it is 43.3%" lost its value to start_value.
Population (2026-11-08):
- p001 "Italy has 20 millions population in 2022": no population indicator in the catalog.
Gallery seeding:
- c001, c018, c029: "latest" in a dated statement was read as today's latest data.
- c002: "has been rising for years" was fitted from 1983.
- c007: a level claim's plan answered with value_at and change; rejected twice.
- c006: 132.0 against "133%" failed a ±0.5 tolerance.
- c024: "fell more than 18%" was checked as exactly 18%.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from holdsup.adapters.base import FetchedSeries, Filters, Observation
from holdsup.catalog.index import IndicatorHit
from holdsup.catalog.schema import load_catalog
from holdsup.config import REPO_ROOT
from holdsup.ops import FlagCode, OpRecord
from holdsup.pipeline.claim import Basis, Operator
from holdsup.pipeline.result import ClaimResult, PipelineOutput
from holdsup.pipeline.run import Pipeline
from holdsup.pipeline.trace import StepEvent
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.verdict import Label, load_tolerances
from tests.router.fakes import FakeClient, FakeClock, config, provider
from tests.service.fakes import explain_answer, reply

CATALOG = load_catalog(REPO_ROOT / "packages" / "catalog")
SERIES = Path(__file__).resolve().parents[1] / "fixtures" / "series"
TODAY = date(2026, 11, 7)


def _key(source: str, dataset: str, filters: Any) -> str:
    return json.dumps([source, dataset, filters], sort_keys=True)


class RecordedFetcher:
    """Serves tests/fixtures/series: what the adapters returned when recorded."""

    def __init__(self) -> None:
        self.docs = {}
        for path in SERIES.glob("*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.docs[_key(doc["source"], doc["dataset"], doc["filters"])] = doc

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        doc = self.docs[_key(source, dataset, dict(filters))]  # KeyError: not recorded
        return FetchedSeries(
            source=source,
            dataset=dataset,
            url=doc["url"],
            retrieved_at=doc["retrieved_at"],
            raw_sha256=doc["raw_sha256"],
            observations=[Observation(g, p, v) for g, p, v in doc["observations"]],
            label=doc["label"],
            updated=doc["updated"],
            citation=doc["citation"],
        )


USED = [
    "unemployment_rate_monthly", "youth_unemployment_rate_monthly", "unemployment_rate_ilo",
    "government_debt_pct_gdp", "government_debt_pct_gdp_quarterly", "greenhouse_gas_emissions",
    "co2_per_capita", "population_total",
]  # fmt: skip
ORDER = [CATALOG.get(i) for i in USED] + [s for s in CATALOG.indicators if s.id not in USED]


async def search(phrase: str, k: int) -> list[IndicatorHit]:
    """The real catalog, the entries these claims use first (no embedding model in tests):
    the matcher keeps the first 8 that cover the claim's place, and the script picks one."""
    return [
        IndicatorHit(id=s.id, name=s.name, source=str(s.source), source_code=s.source_code,
                     unit=s.unit, frequency=str(s.frequency), definition=s.definition,
                     score=1 - i / 100)
        for i, s in enumerate(ORDER[:k])
    ]  # fmt: skip


async def check(text: str, script: list[ChatResponse]) -> tuple[PipelineOutput, FakeClient]:
    client = FakeClient()
    client.script("fake", script)
    steps = {s: ["fake"] for s in ("extract", "match", "plan", "explain")}
    pipeline = Pipeline(
        router=Router(config(provider("fake"), steps=steps), client, clock=FakeClock()),
        catalog=CATALOG,
        search=search,
        fetcher=RecordedFetcher(),
        tolerances=load_tolerances(),
        today=lambda: TODAY,
    )

    async def emit(_: StepEvent) -> None:
        return None

    return await pipeline.run(text, emit), client


def model_claim(
    quote: str,
    phrase: str,
    start: str | None,
    end: str | None,
    *,
    geo: str = "IT",
    lookback: dict[str, Any] | None = None,
    office: dict[str, Any] | None = None,
    **assertion: Any,
) -> dict[str, Any]:
    a = {"type": "level", "value": None, "direction": None, "unit": "%", "start_value": None,
         "end_value": None, **assertion}  # fmt: skip
    return {
        "quote": quote, "indicator_phrase": phrase, "geo": geo, "geo_named": True, "peers": [],
        "start": start, "start_named": start is not None, "end": end, "lookback": lookback,
        "office": office, "assertion": a,
    }  # fmt: skip


def extraction(*claims: Any, speaker: str | None = None) -> ChatResponse:
    return reply({"speaker": speaker, "said_on": None, "claims": list(claims)})


def match(indicator_id: str | None, alternatives: list[str] | None = None) -> ChatResponse:
    reason = (
        "No annual youth unemployment rate indicator is available in the candidates."
        if indicator_id is None
        else "Same measure, population and unit."
    )
    return reply({"indicator_id": indicator_id, "confidence": "high", "reason": reason,
                  "alternatives": alternatives or []})  # fmt: skip


def plan(*calls: dict[str, Any], answer: list[int] | None = None) -> ChatResponse:
    return reply({"calls": list(calls), "answer": answer or [0], "reason": "It answers it."})


EXPLAINED = explain_answer("The data shows what the verdict says.")


def flags(c: ClaimResult) -> set[FlagCode]:
    return {f.code for r in c.operations for f in r.flags}


def flag(r: OpRecord, code: FlagCode) -> str:
    return next(f.detail for f in r.flags if f.code is code)


def inputs(r: OpRecord) -> list[tuple[str, float]]:
    return [(p.period, round(p.value, 2)) for p in r.inputs]


# --- whole years on monthly series, and levels (first live run) ------------------------------

FALL = "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023."
YOUTH = "In 2011 Italy's youth unemployment was 29%; today it is 43.3%."


async def test_r001_a_change_between_whole_years_compares_yearly_averages() -> None:
    script = [
        extraction(model_claim(FALL[:-1], "unemployment rate", "2015", "2023",
                               direction="down", start_value=11.9, end_value=7.7)),
        match("unemployment_rate_monthly", ["unemployment_rate_ilo"]),
        # The live plan: the first and last month instead of the two years.
        plan({"op": "change", "geo": "IT", "start": "2015-01", "end": "2023-12",
              "kind": "percentage_points"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(FALL, script)
    [c] = out.claims

    [op] = c.operations
    assert (op.args["start"], op.args["end"]) == ("2015", "2023")
    assert inputs(op) == [("2015", 12.02), ("2023", 7.68)]
    made = next(f for f in op.flags if f.code is FlagCode.ANNUAL_VALUE)
    assert made.items == ["2015", "2023"] and "average of its 12 monthly values" in made.detail
    assert any("2015-01 → 2015" in n for n in c.notes)
    assert c.verdict.label is Label.SUPPORTED, c.verdict
    assert {p.name: p.period for p in c.verdict.parts} == {
        "assertion": None, "start value": "2015", "end value": "2023",
    }  # fmt: skip
    assert out.versions.catalog == "0.5.0" and out.versions.tolerances == 2


async def test_c004_two_levels_in_one_sentence_are_checked_on_their_own() -> None:
    script = [
        extraction(
            model_claim("In 2011 Italy's youth unemployment was 29%", "youth unemployment rate",
                        "2011", None, start_value=29),
            model_claim("today it is 43.3%", "youth unemployment rate", None, "latest",
                        start_value=43.3),
        ),
        # Claim 1: turned down for being monthly (live), then picked when asked again.
        match(None, ["youth_unemployment_rate_monthly"]),
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "2011"}),
        EXPLAINED,
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "latest"}),
        EXPLAINED,
    ]  # fmt: skip
    out, client = await check(YOUTH, script)
    first, second = out.claims

    assert first.claim.assertion.value == 29 and first.claim.assertion.start_value is None
    assert "level 29 was in assertion.start_value; used as the value" in first.claim.notes
    assert any(n.startswith("asked again: youth_unemployment_rate_monthly") for n in first.notes)
    nudges = [m for _, r in client.calls for m in r.messages
              if "Frequency is not a reason" in str(m.get("content"))]  # fmt: skip
    assert len(nudges) == 1
    assert inputs(first.operations[0]) == [("2011", 29.19)]
    assert first.verdict.label is Label.SUPPORTED and first.verdict.parts[0].period == "2011"

    # No claim date: "today" is the latest month there is, and nothing is cut.
    assert second.claim.assertion.value == 43.3
    assert inputs(second.operations[0]) == [("2026-09", 19.9)]
    assert not flags(second) & {FlagCode.ANNUAL_VALUE, FlagCode.AS_OF}
    assert second.verdict.label is Label.NOT_SUPPORTED
    assert "for 2026-09" in second.verdict.parts[0].detail


async def test_a_plan_month_inside_a_named_year_is_read_as_the_year() -> None:
    text = "In 2011 Italy's youth unemployment was 29%."
    script = [
        extraction(model_claim(text[:-1], "youth unemployment rate", "2011", None, value=29)),
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "2011-06"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(text, script)
    [c] = out.claims
    assert c.operations[0].args["period"] == "2011"
    assert c.verdict.label is Label.SUPPORTED


async def test_a_named_month_is_kept() -> None:
    text = "In June 2011 Italy's youth unemployment was 29%."
    script = [
        extraction(model_claim(text[:-1], "youth unemployment rate", "2011-06", None, value=29)),
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "2011-06"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(text, script)
    [c] = out.claims
    assert c.operations[0].args["period"] == "2011-06"
    assert FlagCode.ANNUAL_VALUE not in flags(c)
    assert c.verdict.parts[0].period == "2011-06"


# --- the gallery claims (second run) ---------------------------------------------------------

C001 = "Renzi, 2018: Since I took office, youth unemployment has fallen 12 points, from 44% to 32%."


async def test_c001_latest_is_the_last_month_published_by_the_claim_date() -> None:
    office = {"who": "Renzi", "scope": "since_start", "previous": False}
    change = {"op": "change", "geo": "IT", "start": "2014-02", "end": "latest",
              "kind": "percentage_points"}  # fmt: skip
    script = [
        extraction(
            model_claim("youth unemployment has fallen 12 points", "youth unemployment rate",
                        None, "latest", office=office, type="percentage_points", value=12,
                        direction="down", unit="points"),
            model_claim("from 44% to 32%", "youth unemployment rate", None, "latest",
                        office=office, direction="down", start_value=44, end_value=32),
            speaker="Renzi",
        ),
        match("youth_unemployment_rate_monthly"), plan(change), EXPLAINED,
        match("youth_unemployment_rate_monthly"), plan(change), EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C001, script)
    points, levels = out.claims

    assert (points.claim.start, points.claim.start_basis) == ("2014-02", Basis.OFFICE)
    [op] = points.operations
    # Said in 2018: the last month out by the end of 2018 is 2018-11, not 2026-09.
    assert inputs(op) == [("2014-02", 42.7), ("2018-11", 32.0)]
    assert op.value == pytest.approx(-10.7)
    note = flag(op, FlagCode.AS_OF)
    assert note.startswith("claim date 2018: latest is the last period published by then, 2018-11")
    assert "today's revised figure" in note
    assert points.verdict.label is Label.NOT_SUPPORTED  # 10.7 points, not 12

    by_part = {p.name: p.holds for p in levels.verdict.parts}
    assert by_part == {"assertion": True, "start value": False, "end value": True}
    assert levels.verdict.label is Label.PARTLY_SUPPORTED  # 42.7 is not "44"; 32.0 is "32"


C002 = "Letta, 2013: Italy's youth unemployment has reached 37% and has been rising for years."


async def test_c002_for_years_is_the_five_years_before_the_claim_date() -> None:
    script = [
        extraction(
            model_claim("Italy's youth unemployment has reached 37%", "youth unemployment rate",
                        None, "2013", value=37),
            model_claim("has been rising for years", "youth unemployment rate", None, "2013",
                        type="trend", direction="up", unit=None),
            speaker="Letta",
        ),
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "2013"}),
        EXPLAINED,
        match("youth_unemployment_rate_monthly"),
        # The live plan: the whole series, from 1983.
        plan({"op": "trend", "geo": "IT", "start": "1983-01", "end": "2013-12"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C002, script)
    level, rising = out.claims

    assert inputs(level.operations[0]) == [("2013", 40.12)]
    assert level.verdict.label is Label.NOT_SUPPORTED  # 37 ± 0.87

    assert (rising.claim.start, rising.claim.start_basis) == ("2008", Basis.ASSUMED)
    assert "'for years' read as the 5 years before the claim date (2013): from 2008" in (
        rising.claim.notes
    )
    [op] = rising.operations
    assert (op.args["start"], op.args["end"]) == ("2008-01", "2013-12")
    assert len(op.inputs) == 72
    assert flag(op, FlagCode.ASSUMED_WINDOW) == (
        "the claim gives no dates: the window is the 5 years before the claim date (2013), "
        "from 2008"
    )
    assert rising.verdict.label is Label.SUPPORTED


C007 = "Grillo: At the end of 2013 Italy's debt-to-GDP ratio hit 132.6%, up from 127% in 2012."


async def test_c007_a_level_claim_is_answered_by_its_value_not_the_change_beside_it() -> None:
    script = [
        extraction(
            model_claim("Italy's debt-to-GDP ratio hit 132.6%", "debt-to-GDP ratio", None, "2013",
                        value=132.6, direction="up"),
            model_claim("Italy's debt-to-GDP ratio ... hit 132.6%, up from 127% in 2012",
                        "debt-to-GDP ratio", None, "2012", value=127, direction="up"),
            speaker="Grillo",
        ),
        match("government_debt_pct_gdp", ["government_debt_pct_gdp_quarterly"]),
        plan({"op": "value_at", "geo": "IT", "period": "2013"}),
        EXPLAINED,
        match("government_debt_pct_gdp", ["government_debt_pct_gdp_quarterly"]),
        # What failed twice live: a level claim answered by value_at and change.
        plan({"op": "value_at", "geo": "IT", "period": "2012"},
             {"op": "change", "geo": "IT", "start": "2012", "end": "2013",
              "kind": "percentage_points"}, answer=[0, 1]),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C007, script)
    end_2013, from_2012 = out.claims

    assert inputs(end_2013.operations[0]) == [("2013", 132.0)]
    assert end_2013.verdict.label is Label.SUPPORTED  # 132.6 ± 1.38
    assert from_2012.answer == [0] and len(from_2012.operations) == 2
    assert "answer [0, 1] → [0]: a level claim is answered by its value_at" in from_2012.notes
    assert inputs(from_2012.operations[0]) == [("2012", 126.1)]
    assert from_2012.verdict.label is Label.SUPPORTED  # 127 ± 1.77
    assert not from_2012.retryable


C006 = "Renzi, 2013: Italy's public debt is 133% of GDP."


async def test_c006_a_level_allows_rounding_plus_one_percent() -> None:
    text = C006
    script = [
        extraction(model_claim(text[13:], "public debt", "2013", "2013", value=133),
                   speaker="Renzi"),
        match("government_debt_pct_gdp", ["government_debt_pct_gdp_quarterly"]),
        match("government_debt_pct_gdp"),  # asked again about the quarterly series: kept annual
        plan({"op": "value_at", "geo": "IT", "period": "2013"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(text, script)
    [c] = out.claims
    [part] = c.verdict.parts
    assert (part.computed, part.asserted) == (132.0, 133.0)
    assert part.tolerance == pytest.approx(0.5 + 1.33)
    assert c.verdict.label is Label.SUPPORTED


async def test_c006_a_statement_about_the_present_is_checked_on_the_quarterly_series() -> None:
    """Live, the annual series was picked and "latest" by end-2013 was 2012 (126.1): not
    supported, against a fact-check that finds 133% right. The quarterly series is out sooner."""
    script = [
        extraction(model_claim(C006[13:], "public debt", None, "2013", value=133),
                   speaker="Renzi"),
        match("government_debt_pct_gdp", ["government_debt_pct_gdp_quarterly"]),
        match("government_debt_pct_gdp_quarterly"),  # asked again: it is out months sooner
        plan({"op": "value_at", "geo": "IT", "period": "2013-Q2"}),  # the cut-off, written out
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C006, script)
    [c] = out.claims
    assert c.indicator is not None and c.indicator.id == "government_debt_pct_gdp_quarterly"
    assert any(n.startswith("asked again: government_debt_pct_gdp_quarterly") for n in c.notes)
    cutoff = "call 0 (value_at): period 2013-Q2 → latest, the last period published by the claim"
    assert any(n.startswith(cutoff) for n in c.notes)
    [op] = c.operations
    assert inputs(op) == [("2013-Q2", 132.6)]  # 2013-Q3 is out in January 2014
    assert "latest is the last period published by then, 2013-Q2" in flag(op, FlagCode.AS_OF)
    [part] = c.verdict.parts
    assert part.tolerance == pytest.approx(0.5 + 1.33)
    assert c.verdict.label is Label.SUPPORTED  # 132.6 against 133 ± 1.83


C018 = "Renzi, December 2015: Italy's greenhouse gas emissions are down 23% compared with 1990."


async def test_c018_latest_respects_a_slow_source_s_release_lag() -> None:
    script = [
        extraction(model_claim(C018[23:], "greenhouse gas emissions", "1990", "latest",
                               type="percent", value=23, direction="down"), speaker="Renzi"),
        match("greenhouse_gas_emissions"),
        plan({"op": "change", "geo": "IT", "start": "1990", "end": "latest", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C018, script)
    [c] = out.claims
    [op] = c.operations
    # By December 2015, inventories ran to 2013 (an 18-month lag), not 2024.
    assert inputs(op) == [("1990", 520.63), ("2013", 450.51)]
    assert op.value == pytest.approx(-13.47, abs=0.01)
    assert "claim date 2015-12: latest is the last period published by then, 2013" in flag(
        op, FlagCode.AS_OF
    )
    assert c.verdict.label is Label.NOT_SUPPORTED


async def test_c018_a_plan_that_writes_the_cutoff_year_still_gets_the_claim_date_note() -> None:
    script = [
        extraction(model_claim(C018[23:], "greenhouse gas emissions", "1990", "latest",
                               type="percent", value=23, direction="down"), speaker="Renzi"),
        match("greenhouse_gas_emissions"),
        plan({"op": "change", "geo": "IT", "start": "1990", "end": "2013", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C018, script)
    [c] = out.claims
    assert c.operations[0].args["end"] == "latest"
    assert inputs(c.operations[0]) == [("1990", 520.63), ("2013", 450.51)]
    assert FlagCode.AS_OF in flags(c)
    assert c.verdict.label is Label.NOT_SUPPORTED


C024 = "EPA, 2017: US per capita carbon dioxide emissions fell more than 18% between 2000 and 2014."


async def test_c024_more_than_is_a_bound() -> None:
    script = [
        extraction(model_claim(C024[11:-1], "US per capita carbon dioxide emissions", "2000",
                               "2014", geo="US", type="percent", value=18, direction="down"),
                   speaker="EPA"),
        match("co2_per_capita"),
        plan({"op": "change", "geo": "US", "start": "2000", "end": "2014", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C024, script)
    [c] = out.claims
    assert c.claim.assertion.operator is Operator.MORE_THAN
    assert "operator more_than from the text" in c.claim.notes
    assert c.operations[0].value == pytest.approx(-20.0, abs=0.01)
    [part] = c.verdict.parts
    assert part.operator is Operator.MORE_THAN
    assert "asserted more than -18" in part.detail
    assert c.verdict.label is Label.SUPPORTED


C029 = (
    "Facebook post, 2013: Unemployment in South Africa has increased by 60% in the past 19 years."
)


async def test_c029_a_lookback_ends_at_the_claim_date() -> None:
    script = [
        extraction(model_claim(C029[21:], "unemployment", None, "latest", geo="ZA",
                               lookback={"amount": 19, "unit": "years"}, type="percent",
                               value=60, direction="up")),
        match("unemployment_rate_ilo"),
        plan({"op": "change", "geo": "ZA", "start": "1994", "end": "latest", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C029, script)
    [c] = out.claims
    assert (c.claim.start, c.claim.start_basis) == ("1994", Basis.LOOKBACK)
    [op] = c.operations
    assert inputs(op) == [("1994", 23.07), ("2012", 24.73)]  # 2012: out by the end of 2013
    assert FlagCode.AS_OF in flags(c)
    assert c.verdict.label is Label.NOT_SUPPORTED  # +7.2%, not +60%


async def test_c029_a_plan_that_writes_the_cutoff_year_still_gets_the_claim_date_note() -> None:
    script = [
        extraction(model_claim(C029[21:], "unemployment", None, "latest", geo="ZA",
                               lookback={"amount": 19, "unit": "years"}, type="percent",
                               value=60, direction="up")),
        match("unemployment_rate_ilo"),
        plan({"op": "change", "geo": "ZA", "start": "1994", "end": "2012", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C029, script)
    [c] = out.claims
    assert c.operations[0].args["end"] == "latest" and FlagCode.AS_OF in flags(c)
    assert inputs(c.operations[0]) == [("1994", 23.07), ("2012", 24.73)]


async def test_c018_a_place_written_as_a_name_is_read_as_its_code() -> None:
    # What the extractor wrote live: "Italy", which dropped the claim for naming no place.
    script = [
        extraction(model_claim(C018[23:], "greenhouse gas emissions", "1990", "latest",
                               geo="Italy", type="percent", value=23, direction="down"),
                   speaker="Renzi"),
        match("greenhouse_gas_emissions"),
        plan({"op": "change", "geo": "IT", "start": "1990", "end": "latest", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C018, script)
    [c] = out.claims
    assert c.claim.geo == "IT" and "geo 'Italy' read as IT" in c.claim.notes
    assert inputs(c.operations[0]) == [("1990", 520.63), ("2013", 450.51)]
    assert c.verdict.label is Label.NOT_SUPPORTED and not c.retryable


async def test_c007_two_values_for_a_change_claim_become_one_change() -> None:
    # What the planner wrote live for a "from X to Y" change: one value_at per end.
    script = [
        extraction(model_claim("Italy's debt-to-GDP ratio ... hit 132.6%, up from 127% in 2012",
                               "debt-to-GDP ratio", "2012", "2013", type="percentage_points",
                               value=5.6, direction="up", start_value=127, end_value=132.6),
                   speaker="Grillo"),
        match("government_debt_pct_gdp", ["government_debt_pct_gdp_quarterly"]),
        plan({"op": "value_at", "geo": "IT", "period": "2012"},
             {"op": "value_at", "geo": "IT", "period": "2013"}, answer=[0, 1]),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C007, script)
    [c] = out.claims
    assert not c.retryable and c.verdict.label is not Label.CANT_CHECK
    assert [(o.op, o.args["start"], o.args["end"]) for o in c.operations] == [
        ("change", "2012", "2013")
    ]
    assert c.answer == [0]
    assert inputs(c.operations[0]) == [("2012", 126.1), ("2013", 132.0)]
    assert any("two value_at (2012, 2013) → one change" in n for n in c.notes)


ITALY = "Italy has 20 millions population in 2022."


async def test_p001_total_population_is_in_the_catalog_and_checks_a_headcount() -> None:
    script = [
        extraction(model_claim(ITALY[:-1], "population of Italy", "2022", "2022",
                               unit="million people", value=20)),
        match("population_total", ["population_total_world"]),
        plan({"op": "value_at", "geo": "IT", "period": "2022"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(ITALY, script)
    [c] = out.claims
    assert c.indicator is not None and c.indicator.source_code == "demo_pjan"
    assert inputs(c.operations[0]) == [("2022", 59030133.0)]
    assert c.verdict.label is Label.NOT_SUPPORTED, c.verdict
    assert c.extra_sources == []  # a population claim needs no second series


async def test_the_population_denominator_is_fetched_and_cited_for_per_capita() -> None:
    claim_text = "Italy emitted about 6 tonnes of greenhouse gases per person in 2022."
    script = [
        extraction(model_claim(claim_text[:-1], "greenhouse gas emissions per person", "2022",
                               "2022", unit="tonnes", value=6)),
        match("greenhouse_gas_emissions"),
        plan({"op": "per_capita", "geo": "IT", "population": "population_total"},
             {"op": "value_at", "series": "@0", "geo": "IT", "period": "2022"}, answer=[1]),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(claim_text, script)
    [c] = out.claims
    assert [o.op for o in c.operations] == ["per_capita", "value_at"]
    assert c.verdict.label is not Label.CANT_CHECK, c.verdict
    [extra] = c.extra_sources
    assert (extra.indicator.id, extra.data.dataset) == ("population_total", "demo_pjan")


def test_the_smoke_set_names_real_indicators_and_labels() -> None:
    lines = (REPO_ROOT / "eval" / "smoke_claims.jsonl").read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    texts = {c["text"] for c in cases}
    assert {FALL, YOUTH, C001, C002, C006, C007, C018, C024, C029, ITALY} <= texts
    ids = [c["id"] for c in cases]
    assert len(set(ids)) == len(ids)
    for case in cases:
        for c in case["claims"]:
            CATALOG.get(c["indicator"])  # KeyError if the entry is gone
            assert Label(c["expected"]) and c["quote"] in case["text"] and c["justification"]
