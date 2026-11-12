"""Re-checking a claim with a statistic the reader chose (P3.7), on the real catalog and recorded
data: the claim as the first check read it, no extract or match model call, and the rest of
the pipeline as usual."""

from holdsup.pipeline.result import ClaimResult, PipelineOutput, Suggestion
from holdsup.pipeline.run import CHOSEN, GONE, REUSED, Choice, Pipeline
from holdsup.pipeline.trace import Step, StepEvent
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.verdict import Label, load_tolerances
from tests.pipeline.test_regressions import (
    C006,
    CATALOG,
    EXPLAINED,
    TODAY,
    RecordedFetcher,
    check,
    extraction,
    match,
    model_claim,
    plan,
    search,
)
from tests.router.fakes import FakeClient, FakeClock, config, provider

ANNUAL, QUARTERLY = "government_debt_pct_gdp", "government_debt_pct_gdp_quarterly"


async def first() -> ClaimResult:
    """Renzi's 133% (c006), matched to the yearly series, the quarterly one its alternative."""
    script = [
        extraction(model_claim(C006[13:], "public debt", "2013", "2013", value=133),
                   speaker="Renzi"),
        match(ANNUAL, [QUARTERLY]),
        match(ANNUAL, [QUARTERLY]),  # asked again about the quarterly series: kept annual
        plan({"op": "value_at", "geo": "IT", "period": "2013"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C006, script)
    return out.claims[0]


async def recheck(
    claim: ClaimResult, choice: Choice, script: list[ChatResponse]
) -> tuple[PipelineOutput, FakeClient, list[StepEvent]]:
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
    events: list[StepEvent] = []

    async def emit(event: StepEvent) -> None:
        events.append(event)

    return await pipeline.recheck(claim.claim, choice, emit), client, events


async def test_a_matched_claim_offers_its_alternatives_by_name() -> None:
    c = await first()
    assert c.indicator is not None and c.indicator.id == ANNUAL
    assert c.suggestions == [Suggestion(id=QUARTERLY, name=CATALOG.get(QUARTERLY).name)]


async def test_a_recheck_reads_the_claim_once_and_uses_the_reader_s_statistic() -> None:
    c = await first()
    script = [plan({"op": "value_at", "geo": "IT", "period": "2013-Q4"}), EXPLAINED]
    out, client, events = await recheck(c, Choice(QUARTERLY, (ANNUAL,)), script)
    [r] = out.claims
    assert r.claim == c.claim  # as the first check read it
    assert r.indicator is not None and r.indicator.id == QUARTERLY
    assert r.match_reason == CHOSEN
    # The new result offers the first check's statistic in turn.
    assert r.alternatives == [ANNUAL]
    assert r.suggestions == [Suggestion(id=ANNUAL, name=CATALOG.get(ANNUAL).name)]
    assert r.data is not None and r.data.dataset == CATALOG.get(QUARTERLY).source_code
    assert r.verdict.label is not Label.CANT_CHECK, r.verdict
    # Only the plan and the explanation asked a model.
    assert len(client.calls) == 2 and [m.step for m in r.models] == [Step.PLAN, Step.EXPLAIN]
    assert out.models == []
    done = [(e.step, e.summary) for e in events if e.event == "step_done"]
    assert done[0] == (Step.EXTRACT, REUSED)
    quarterly = CATALOG.get(QUARTERLY)
    using = f"Using {quarterly.name} (eurostat {quarterly.source_code}), as chosen."
    assert done[1] == (Step.MATCH, using)


async def test_a_statistic_gone_from_the_catalog_cannot_be_checked() -> None:
    c = await first()
    out, client, _ = await recheck(c, Choice("retired_statistic", (ANNUAL, "also_gone")), [])
    [r] = out.claims
    assert r.verdict.label is Label.CANT_CHECK and r.verdict.reason == GONE
    assert r.stopped_at is Step.MATCH and client.calls == []
