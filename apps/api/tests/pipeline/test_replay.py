"""Computing a stored claim again from its plan, with code alone (S1, the claim watch): the same
figures give the same result, a revised figure counts, a figure published since does not, and
anything that keeps the claim from being computed raises `ReplayError`."""

from collections.abc import Callable
from dataclasses import replace

import pytest

from holdsup.adapters.base import FetchedSeries, Filters, Observation, SourceUnavailable
from holdsup.ops import FlagCode
from holdsup.pipeline.result import ClaimResult
from holdsup.pipeline.steps import CodeSteps, ReplayError, cut_at, read_extents
from holdsup.pipeline.trace import Step
from holdsup.verdict import Label, cant_check, load_tolerances
from tests.pipeline.test_regressions import (
    CATALOG,
    EXPLAINED,
    FALL,
    TODAY,
    YOUTH,
    RecordedFetcher,
    check,
    extraction,
    inputs,
    match,
    model_claim,
    plan,
)

Change = Callable[[Observation], Observation | None]


class EditedFetcher(RecordedFetcher):
    """The recorded data, with each observation passed through `edit` (None drops it), and
    `added` appended: what a source might serve after a revision or a new release."""

    def __init__(self, edit: Change | None = None, added: list[Observation] | None = None):
        super().__init__()
        self.edit = edit
        self.added = added or []

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        series = await super().fetch_series(source, dataset, filters)
        kept = [e for o in series.observations if (e := self._edit(o)) is not None]
        return replace(series, observations=kept + self.added, raw_sha256="new")

    def _edit(self, o: Observation) -> Observation | None:
        return self.edit(o) if self.edit else o


class DownFetcher(RecordedFetcher):
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        raise SourceUnavailable("503")


def steps(fetcher: RecordedFetcher | None = None) -> CodeSteps:
    """The code's steps alone: no router, no search, no reranker."""
    return CodeSteps(
        catalog=CATALOG,
        fetcher=fetcher or RecordedFetcher(),
        tolerances=load_tolerances(),
        today=lambda: TODAY,
    )


async def fall() -> ClaimResult:
    """r001: Italy's unemployment fell from 11.9% in 2015 to 7.7% in 2023 (monthly series)."""
    script = [
        extraction(model_claim(FALL[:-1], "unemployment rate", "2015", "2023",
                               direction="down", start_value=11.9, end_value=7.7)),
        match("unemployment_rate_monthly", ["unemployment_rate_ilo"]),
        plan({"op": "change", "geo": "IT", "start": "2015-01", "end": "2023-12",
              "kind": "percentage_points"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(FALL, script)
    return out.claims[0]


async def today_level() -> ClaimResult:
    """c004's second claim: "today it is 43.3%", with no claim date (latest is 2026-09)."""
    script = [
        extraction(model_claim("today it is 43.3%", "youth unemployment rate", None, "latest",
                               start_value=43.3)),
        match("youth_unemployment_rate_monthly"),
        plan({"op": "value_at", "geo": "IT", "period": "latest"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(YOUTH, script)
    return out.claims[0]


def figures(c: ClaimResult) -> tuple[object, ...]:
    return (c.operations, c.series, c.sweep, c.changepoints, c.distortion_checks, c.verdict)


async def test_a_checked_claim_stores_its_plan_and_where_each_series_ended() -> None:
    c = await fall()
    assert c.plan is not None
    # The plan as code accepted it: the months were read as the years.
    [call] = c.plan.calls
    assert (call.op, call.start, call.end) == ("change", "2015", "2023")
    monthly = c.plan.read_until["unemployment_rate_monthly"]
    assert monthly["IT"] == "2026-09"


async def test_the_same_figures_give_the_same_result_with_no_model() -> None:
    c = await fall()
    again = await steps().replay(c, TODAY)
    assert figures(again) == figures(c)
    assert again.confidence == c.confidence
    # Everything the first check's models chose is kept; only the explanation is the code's.
    assert (again.claim, again.indicator, again.plan) == (c.claim, c.indicator, c.plan)
    assert again.explanation_source == "template" and again.explanation
    assert [m.step for m in again.models] == [
        m.step for m in c.models if m.step is not Step.EXPLAIN
    ]
    assert again.data is not None and c.data is not None
    assert again.data.raw_sha256 == c.data.raw_sha256


async def test_a_revised_figure_counts() -> None:
    c = await fall()

    def revise(o: Observation) -> Observation:
        up = o.geo == "IT" and o.period.startswith("2023") and o.value is not None
        return replace(o, value=o.value + 1.5) if up and o.value is not None else o

    again = await steps(EditedFetcher(revise)).replay(c, TODAY)
    assert inputs(again.operations[0]) == [("2015", 12.02), ("2023", 9.18)]
    assert c.verdict.label is Label.SUPPORTED
    assert again.verdict.label is Label.PARTLY_SUPPORTED  # the end value no longer holds
    assert again.data is not None and again.data.raw_sha256 == "new"


async def test_a_figure_published_since_does_not_count() -> None:
    c = await today_level()
    assert inputs(c.operations[0]) == [("2026-09", 19.9)]
    later = [Observation("IT", "2026-10", 43.3), Observation("IT", "2026-11", 43.3)]
    again = await steps(EditedFetcher(added=later)).replay(c, TODAY)
    assert figures(again) == figures(c)
    assert not {f.code for r in again.operations for f in r.flags} & {FlagCode.AS_OF}


async def test_a_place_with_no_figures_then_is_left_out() -> None:
    assert cut_at(
        [Observation("IT", "2024", 1.0), Observation("IT", "2025", 2.0),
         Observation("FR", "2024", 3.0), Observation("IT", "bad", 4.0)],
        {"IT": "2024"},
    ) == [Observation("IT", "2024", 1.0)]  # fmt: skip


def test_extents_skip_gaps_and_periods_that_do_not_parse() -> None:
    data = {
        "a": [Observation("IT", "2024", 1.0), Observation("IT", "2025", None),
              Observation("FR", "2023-Q4", 2.0), Observation("FR", "2024-Q1", 3.0),
              Observation("DE", "someday", 4.0)],
        "b": [],
    }  # fmt: skip
    assert read_extents(data) == {"a": {"FR": "2024-Q1", "IT": "2024"}, "b": {}}


@pytest.mark.parametrize(
    ("fetcher", "error"),
    [
        (DownFetcher(), "didn't answer just now"),
        # Italy's figures gone from the series.
        (EditedFetcher(lambda o: None if o.geo == "IT" else o), "has no Unemployment"),
    ],
)
async def test_a_source_that_cannot_give_the_figures_stops_the_replay(
    fetcher: RecordedFetcher, error: str
) -> None:
    c = await fall()
    with pytest.raises(ReplayError, match=error):
        await steps(fetcher).replay(c, TODAY)


async def test_a_calculation_that_can_no_longer_finish_stops_the_replay() -> None:
    c = await fall()
    # Italy's figures withdrawn after 2015: no 2023 to compare with.
    cut = EditedFetcher(lambda o: None if o.geo == "IT" and o.period > "2016" else o)
    with pytest.raises(ReplayError, match="couldn't finish the calculation"):
        await steps(cut).replay(c, TODAY)


async def test_figures_that_no_longer_decide_the_claim_stop_the_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c = await fall()
    monkeypatch.setattr("holdsup.pipeline.steps.decide", lambda *_, **__: cant_check("gone"))
    with pytest.raises(ReplayError, match="no longer decide the claim: gone"):
        await steps().replay(c, TODAY)


async def test_a_claim_with_no_stored_plan_or_a_retired_statistic_cannot_be_replayed() -> None:
    c = await fall()
    with pytest.raises(ReplayError, match="no stored plan"):
        await steps().replay(c.model_copy(update={"plan": None}), TODAY)
    assert c.indicator is not None
    retired = c.indicator.model_copy(update={"id": "retired_statistic"})
    with pytest.raises(ReplayError, match="no longer in the catalog"):
        await steps().replay(c.model_copy(update={"indicator": retired}), TODAY)


async def per_person() -> ClaimResult:
    text = "Italy emitted about 6 tonnes of greenhouse gases per person in 2022."
    script = [
        extraction(model_claim(text[:-1], "greenhouse gas emissions per person", "2022",
                               "2022", unit="tonnes", value=6)),
        match("greenhouse_gas_emissions"),
        plan({"op": "per_capita", "geo": "IT", "population": "population_total"},
             {"op": "value_at", "series": "@0", "geo": "IT", "period": "2022"}, answer=[1]),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(text, script)
    return out.claims[0]


class NoPopulation(RecordedFetcher):
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        if dataset == CATALOG.get("population_total").source_code:
            raise SourceUnavailable("503")
        return await super().fetch_series(source, dataset, filters)


async def test_a_per_person_claim_is_replayed_with_its_population() -> None:
    c = await per_person()
    assert c.plan is not None and set(c.plan.read_until) >= {
        "greenhouse_gas_emissions", "population_total"
    }  # fmt: skip
    again = await steps().replay(c, TODAY)
    assert figures(again) == figures(c) and again.extra_sources == c.extra_sources
    with pytest.raises(ReplayError, match="no figures for population_total"):
        await steps(NoPopulation()).replay(c, TODAY)
