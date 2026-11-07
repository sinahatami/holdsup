"""Regression tests for claims that came out wrong in the first live run (2026-11-07).

Recorded Eurostat data (une_rt_m for Italy, seasonally adjusted, 2010-01 to 2026-09), the real
catalog, and scripted model replies that reproduce what the models answered live:

1. "fell from 11.9% in 2015 to 7.7% in 2023": the plan compared 2015-01 with 2023-12 on the
   monthly series; a whole year must be the year's average.
2. "In 2011 ... was 29%": the matcher turned the monthly youth series down for being monthly.
3. "today it is 43.3%": extraction put the level in start_value, so nothing was checked.

The same claims are in eval/smoke_claims.jsonl.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from holdsup.adapters.base import FetchedSeries, Filters, sha256_hex
from holdsup.adapters.jsonstat import observations, parse_cube
from holdsup.catalog.index import IndicatorHit
from holdsup.catalog.schema import load_catalog
from holdsup.config import REPO_ROOT
from holdsup.ops import FlagCode
from holdsup.pipeline.run import ClaimResult, Pipeline, PipelineOutput, StepEvent
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.verdict import Label, load_tolerances
from tests.router.fakes import FakeClient, FakeClock, config, provider
from tests.service.fakes import explain_answer, reply

CATALOG = load_catalog(REPO_ROOT / "packages" / "catalog")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "eurostat"
RECORDED = {
    "TOTAL": FIXTURES / "une_rt_m_it_total_sa.json",
    "Y_LT25": FIXTURES / "une_rt_m_it_youth_sa.json",
}
FALL = "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023."
YOUTH = "In 2011 Italy's youth unemployment was 29%; today it is 43.3%."


class RecordedEurostat:
    """Serves the recorded une_rt_m responses through the real JSON-stat parser."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls.append(dict(filters))
        assert (source, dataset) == ("eurostat", "une_rt_m")
        body = RECORDED[str(filters["age"])].read_bytes()
        cube = parse_cube(body)
        return FetchedSeries(
            source=source,
            dataset=dataset,
            url=f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}",
            retrieved_at=datetime(2026, 11, 7, 17, 3, tzinfo=UTC),
            raw_sha256=sha256_hex(body),
            observations=observations(cube),
            label=cube.label,
        )


async def search(phrase: str, k: int) -> list[IndicatorHit]:
    """The real catalog, monthly unemployment entries first (no embedding model in tests)."""
    first = [
        "youth_unemployment_rate_monthly",
        "unemployment_rate_monthly",
        "unemployment_rate_ilo",
    ]
    specs = [CATALOG.get(i) for i in first]
    specs += [s for s in CATALOG.indicators if s.id not in first]
    return [
        IndicatorHit(**s.model_dump(include={"id", "name", "source_code", "unit", "definition"}),
                     source=str(s.source), frequency=str(s.frequency), score=1 - i / 100)
        for i, s in enumerate(specs[:k])
    ]  # fmt: skip


async def check(text: str, script: list[ChatResponse]) -> tuple[PipelineOutput, FakeClient]:
    client = FakeClient()
    client.script("fake", script)
    steps = {s: ["fake"] for s in ("extract", "match", "plan", "explain")}
    pipeline = Pipeline(
        router=Router(config(provider("fake"), steps=steps), client, clock=FakeClock()),
        catalog=CATALOG,
        search=search,
        fetcher=RecordedEurostat(),
        tolerances=load_tolerances(),
        today=lambda: date(2026, 11, 7),
    )

    async def emit(_: StepEvent) -> None:
        return None

    return await pipeline.run(text, emit), client


def model_claim(quote: str, phrase: str, start: str | None, end: str | None, **a: Any) -> Any:
    assertion = {"type": "level", "value": None, "direction": None, "unit": "%",
                 "start_value": None, "end_value": None, **a}  # fmt: skip
    return {
        "quote": quote, "indicator_phrase": phrase, "geo": "IT", "geo_named": True, "peers": [],
        "start": start, "start_named": start is not None, "end": end, "lookback": None,
        "office": None, "assertion": assertion,
    }  # fmt: skip


def extraction(*claims: Any) -> ChatResponse:
    return reply({"speaker": None, "said_on": None, "claims": list(claims)})


def match(indicator_id: str | None, alternatives: list[str] | None = None) -> ChatResponse:
    reason = (
        "No annual youth unemployment rate indicator is available in the candidates."
        if indicator_id is None
        else "Same measure, population and unit."
    )
    return reply({"indicator_id": indicator_id, "confidence": "high", "reason": reason,
                  "alternatives": alternatives or []})  # fmt: skip


def plan(call: dict[str, Any]) -> ChatResponse:
    return reply({"calls": [call], "answer": [0], "reason": "One operation answers it."})


EXPLAINED = explain_answer("The data shows what the verdict says.")


def flags(c: ClaimResult) -> set[FlagCode]:
    return {f.code for r in c.operations for f in r.flags}


async def test_a_change_between_whole_years_compares_yearly_averages() -> None:
    script = [
        # What the model answered live: both levels, no change value.
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
    assert [(p.period, round(p.value, 2)) for p in op.inputs] == [("2015", 12.02), ("2023", 7.68)]
    assert op.value == pytest.approx(7.68 - 12.02, abs=0.01)
    [made] = [f for f in op.flags if f.code is FlagCode.ANNUAL_VALUE]
    assert made.items == ["2015", "2023"] and "average of its 12 monthly values" in made.detail
    assert any("2015-01 → 2015" in n for n in c.notes)
    assert any("2023-12 → 2023" in n for n in c.notes)

    assert c.verdict.label is Label.SUPPORTED, c.verdict
    assert {p.name: p.period for p in c.verdict.parts} == {
        "assertion": None, "start value": "2015", "end value": "2023",
    }  # fmt: skip
    assert out.versions.catalog == "0.3.0"


async def test_two_levels_in_one_sentence_are_checked_on_their_own() -> None:
    script = [
        # What the model answered live: two level claims, each number in start_value.
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
        # Claim 2: the live match and plan.
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "latest"}),
        EXPLAINED,
    ]  # fmt: skip
    out, client = await check(YOUTH, script)
    first, second = out.claims

    assert first.claim.assertion.value == 29 and first.claim.assertion.start_value is None
    assert "level 29 was in assertion.start_value; used as the value" in first.claim.notes
    assert first.indicator is not None and first.indicator.id == "youth_unemployment_rate_monthly"
    assert any(n.startswith("asked again: youth_unemployment_rate_monthly") for n in first.notes)
    [nudge] = [m for _, r in client.calls for m in r.messages
               if "Frequency is not a reason" in str(m.get("content"))]  # fmt: skip
    assert "average of the year's months" in str(nudge["content"])
    assert [(p.period, round(p.value, 2)) for p in first.operations[0].inputs] == [("2011", 29.19)]
    assert FlagCode.ANNUAL_VALUE in flags(first)
    assert first.verdict.label is Label.SUPPORTED
    assert first.verdict.parts[0].period == "2011"

    assert second.claim.assertion.value == 43.3
    assert [(p.period, p.value) for p in second.operations[0].inputs] == [("2026-09", 19.9)]
    assert FlagCode.ANNUAL_VALUE not in flags(second)  # "today" is the latest month
    assert second.verdict.label is Label.NOT_SUPPORTED
    assert second.verdict.parts[0].period == "2026-09"
    assert "for 2026-09" in second.verdict.parts[0].detail


async def test_a_plan_month_inside_a_named_year_is_read_as_the_year() -> None:
    script = [
        extraction(model_claim("In 2011 Italy's youth unemployment was 29%",
                               "youth unemployment rate", "2011", None, value=29)),
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "2011-06"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check("In 2011 Italy's youth unemployment was 29%.", script)
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


def test_the_smoke_set_names_real_indicators_and_labels() -> None:
    lines = (REPO_ROOT / "eval" / "smoke_claims.jsonl").read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    texts = {c["text"] for c in cases}
    assert {FALL, YOUTH} <= texts  # this file's claims are in the smoke set
    ids = [c["id"] for c in cases]
    assert len(set(ids)) == len(ids)
    for case in cases:
        for c in case["claims"]:
            CATALOG.get(c["indicator"])  # KeyError if the entry is gone
            assert Label(c["expected"]) and c["quote"] in case["text"] and c["justification"]
