"""The same measure from another source, when the matched series has no figures for the
claim's years: which years are missing, and the fetch step reading the other source."""

from dataclasses import dataclass, field

import pytest

from holdsup.adapters.base import FetchedSeries, Filters, Observation, SourceUnavailable
from holdsup.catalog.schema import Catalog, IndicatorSpec
from holdsup.catalog.schema import Frequency as CatalogFrequency
from holdsup.ops import Frequency
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.result import ClaimResult
from holdsup.pipeline.run import Choice
from holdsup.pipeline.same_measure import claim_years, missing_years, slack_years, swap_note
from holdsup.pipeline.trace import StepEvent
from holdsup.verdict import Label
from tests.service.fakes import (
    CATALOG,
    RETRIEVED,
    TEXT,
    UNEMPLOYMENT_IT,
    FakeFetcher,
    claim_json,
    explain_answer,
    extraction,
    make_pipeline,
    match_answer,
    observations,
    plan_answer,
)

MAIN = CATALOG.get("unemployment_rate").model_copy(
    update={"related": ["youth_unemployment_rate", "unemployment_rate_world"],
            "same_measure": ["unemployment_rate_world"]}
)  # fmt: skip
TWIN = IndicatorSpec.model_validate(
    {
        **CATALOG.get("unemployment_rate").model_dump(mode="json"),
        "id": "unemployment_rate_world",
        "source": "worldbank",
        "source_code": "SL.UEM.TOTL.ZS",
        "name": "Unemployment rate, world",
        "geo_coverage": ["All countries"],
        "filters": {},
        "related": ["unemployment_rate"],
        "same_measure": ["unemployment_rate"],
    }
)
PAIRED = Catalog(
    version=CATALOG.version,
    indicators=tuple(MAIN if s.id == MAIN.id else s for s in CATALOG.indicators) + (TWIN,),
)
GAP = {"annual": 1, "monthly": 3}
LATE = {p: v for p, v in UNEMPLOYMENT_IT.items() if p >= "2018"}  # no 2015, nor 2014 or 2016


def claim(start: str | None, end: str | None) -> ClaimSpec:
    extracted_only = ("geo_named", "start_named", "lookback", "office")
    payload = {k: v for k, v in claim_json().items() if k not in extracted_only}
    payload.update(start=start, end=end, geo_basis=None, start_basis=None, end_basis=None,
                   speaker=None, said_on=None)  # fmt: skip
    return ClaimSpec.model_validate(payload)


def test_claim_years_are_the_years_its_start_and_end_fall_in() -> None:
    assert claim_years(claim("2015", "2023")) == [2015, 2023]
    assert claim_years(claim("2015-03", "latest")) == [2015]
    assert claim_years(claim(None, "latest")) == []


def test_a_year_counts_as_covered_within_the_gap_an_annual_series_allows() -> None:
    rows = observations({"IT": {"2016": 1.0, "2020": 2.0}, "FR": {"2015": 3.0}})
    rows.append(Observation("IT", "2010", None))  # a period with no number does not count
    assert missing_years([2010, 2015, 2018, 2021, 2023], rows, "IT", 1) == [2010, 2018, 2023]
    assert missing_years([2015], rows, "IT", 0) == [2015]
    assert missing_years([2015], rows, "ES", 1) == [2015]  # a place with no rows lacks all
    assert missing_years([], rows, "IT", 1) == []


def test_only_an_annual_series_reads_a_neighbouring_year() -> None:
    gap = {Frequency(k): v for k, v in GAP.items()}
    assert slack_years(MAIN, gap) == 1
    monthly = MAIN.model_copy(update={"frequency": CatalogFrequency.MONTHLY})
    assert slack_years(monthly, gap) == 0


def test_the_note_names_both_sources_the_place_and_the_years() -> None:
    assert swap_note(MAIN, TWIN, "IT", [2015]) == (
        "Eurostat has no figures for Italy in 2015, so the same measure from the World Bank "
        "was used."
    )


@dataclass
class BySeries(FakeFetcher):
    """Rows per dataset; a dataset in `down` does not answer."""

    by_dataset: dict[str, list[Observation]] = field(default_factory=dict)
    down: frozenset[str] = frozenset()

    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        self.calls.append((source, dataset, dict(filters)))
        if dataset in self.down:
            raise SourceUnavailable(dataset)
        return FetchedSeries(
            source=source, dataset=dataset, url=f"https://example.invalid/{dataset}",
            retrieved_at=RETRIEVED, raw_sha256="ab" * 32,
            observations=self.by_dataset[dataset], label=dataset,
        )  # fmt: skip


def fetcher(
    main: dict[str, float], twin: dict[str, float], down: frozenset[str] = frozenset()
) -> BySeries:
    return BySeries(
        by_dataset={
            "une_rt_a": observations({"IT": main}),
            "SL.UEM.TOTL.ZS": observations({"ITA": twin}),  # World Bank codes, as it sends them
        },
        down=down,
    )


async def check(source: BySeries) -> tuple[ClaimResult, dict[str, str]]:
    script = [extraction(claim_json()), match_answer(), plan_answer(), explain_answer()]
    pipeline, _, _ = make_pipeline(script, source, catalog=PAIRED)
    events: list[StepEvent] = []

    async def emit(event: StepEvent) -> None:
        events.append(event)

    out = await pipeline.run(TEXT, emit)
    summaries = {str(e.step): e.summary or "" for e in events if e.event == "step_done"}
    return out.claims[0], summaries


def datasets(source: BySeries) -> list[str]:
    return [dataset for _, dataset, _ in source.calls]


async def test_a_year_the_matched_series_lacks_is_read_from_the_same_measure() -> None:
    source = fetcher(LATE, UNEMPLOYMENT_IT)
    c, summaries = await check(source)

    assert c.verdict.label is Label.SUPPORTED
    assert c.operations[0].value == pytest.approx(-4.2)
    assert c.indicator is not None and c.indicator.id == "unemployment_rate_world"
    assert c.data is not None and c.data.dataset == "SL.UEM.TOTL.ZS"
    assert datasets(source)[:2] == ["une_rt_a", "SL.UEM.TOTL.ZS"]
    note = swap_note(MAIN, TWIN, "IT", [2015])
    assert note in c.notes
    assert summaries["match"] == "Matched Unemployment rate (eurostat une_rt_a)."
    assert summaries["fetch"] == f"{note} Fetched 9 rows, 2015 to 2023."
    # The match's own record stays: what was matched, and why.
    assert c.match_reason == "Same measure and unit."


@pytest.mark.parametrize("main", [UNEMPLOYMENT_IT, {**LATE, "2016": 11.7}])
async def test_a_series_that_can_answer_is_kept(main: dict[str, float]) -> None:
    """Every year there, or a neighbour within the allowed gap: no other source is asked."""
    source = fetcher(main, UNEMPLOYMENT_IT)
    c, _ = await check(source)
    assert c.indicator is not None and c.indicator.id == "unemployment_rate"
    assert datasets(source)[:1] == ["une_rt_a"] and "SL.UEM.TOTL.ZS" not in datasets(source)
    assert c.verdict.label is not Label.CANT_CHECK


@pytest.mark.parametrize(
    "source",
    [
        fetcher(LATE, LATE),  # the other source lacks the year too
        fetcher(LATE, UNEMPLOYMENT_IT, down=frozenset({"SL.UEM.TOTL.ZS"})),  # or is down
    ],
)
async def test_without_a_better_source_the_matched_one_stays(source: BySeries) -> None:
    c, summaries = await check(source)
    assert c.indicator is not None and c.indicator.id == "unemployment_rate"
    assert datasets(source)[:2] == ["une_rt_a", "SL.UEM.TOTL.ZS"]
    assert summaries["fetch"] == "Fetched 6 rows, 2018 to 2023."
    # As before: the calculation finds no value near 2015, and that is not worth a retry.
    assert c.verdict.label is Label.CANT_CHECK and str(c.stopped_at) == "execute"
    assert not c.retryable


async def test_a_readers_pick_keeps_its_statistic() -> None:
    first, _ = await check(fetcher(LATE, UNEMPLOYMENT_IT))
    source = fetcher(LATE, UNEMPLOYMENT_IT)
    pipeline, _, _ = make_pipeline([plan_answer(), explain_answer()], source, catalog=PAIRED)

    async def emit(event: StepEvent) -> None:
        pass

    out = await pipeline.recheck(first.claim, Choice("unemployment_rate"), emit)
    [c] = out.claims
    assert datasets(source) == ["une_rt_a"]
    assert c.indicator is not None and c.indicator.id == "unemployment_rate"
    assert c.verdict.label is Label.CANT_CHECK


async def test_another_source_without_the_place_is_not_asked() -> None:
    elsewhere = TWIN.model_copy(update={"geo_coverage": ["DE"]})
    catalog = PAIRED.model_copy(
        update={"indicators": tuple(elsewhere if s.id == TWIN.id else s for s in PAIRED.indicators)}
    )
    source = fetcher(LATE, UNEMPLOYMENT_IT)
    script = [extraction(claim_json()), match_answer(), plan_answer(), explain_answer()]
    pipeline, _, _ = make_pipeline(script, source, catalog=catalog)

    async def emit(event: StepEvent) -> None:
        pass

    [c] = (await pipeline.run(TEXT, emit)).claims
    assert "SL.UEM.TOTL.ZS" not in datasets(source)
    assert c.indicator is not None and c.indicator.id == "unemployment_rate"
