"""The whole check, step by step, with a scripted provider and a fake data source."""

from collections.abc import Sequence

import pytest

from holdsup.adapters.base import SourceNotFound, SourceUnavailable
from holdsup.pipeline.claim import AssertionType
from holdsup.pipeline.plan.prompt import PLAN_FAILED
from holdsup.pipeline.result import PipelineOutput
from holdsup.pipeline.run import NO_CLAIM, NO_MATCH, NO_PLACE
from holdsup.pipeline.trace import Step, StepEvent
from holdsup.router import RouterError
from holdsup.router.client import ChatResponse
from holdsup.router.errors import ProviderError, ProviderUnavailable
from holdsup.verdict import Label
from holdsup.verdict.rules import unsupported_reason
from tests.service.fakes import (
    EXPLANATION,
    TEXT,
    UNEMPLOYMENT_IT,
    FakeFetcher,
    claim_json,
    explain_answer,
    extraction,
    happy_script,
    make_pipeline,
    match_answer,
    observations,
    plan_answer,
    reply,
)

Script = Sequence[ChatResponse | ProviderError]


async def run(
    script: Script, fetcher: FakeFetcher | None = None
) -> tuple[PipelineOutput, list[StepEvent], int, FakeFetcher]:
    pipeline, client, fetcher = make_pipeline(script, fetcher)
    events: list[StepEvent] = []

    async def emit(event: StepEvent) -> None:
        events.append(event)

    out = await pipeline.run(TEXT, emit)
    return out, events, len(client.calls), fetcher


def trace(events: list[StepEvent]) -> list[tuple[str, str, str | None]]:
    return [(e.event, str(e.step), e.status) for e in events]


def done(events: list[StepEvent]) -> list[tuple[str, str | None]]:
    return [(str(e.step), e.status) for e in events if e.event == "step_done"]


async def test_a_supported_claim_runs_every_step() -> None:
    script = [extraction(claim_json()), match_answer(), plan_answer(), explain_answer()]
    out, events, calls, fetcher = await run(script)

    assert calls == 4  # extract, match, plan, explain
    assert done(events) == [
        ("extract", "ok"), ("match", "ok"), ("fetch", "ok"), ("plan", "ok"),
        ("execute", "ok"), ("verdict", "ok"), ("explain", "ok"),
    ]  # fmt: skip
    # Every step starts before it finishes, and only claim steps carry the claim index.
    starts = [e for e in events if e.event == "step_started"]
    assert [s.step for s in starts] == [Step(s) for s, _ in done(events)]
    assert {e.claim for e in events if e.step is not Step.EXTRACT} == {0}
    assert all(e.ms is not None and e.ms >= 0 for e in events if e.event == "step_done")

    [c] = out.claims
    assert c.verdict.label is Label.SUPPORTED
    assert c.stopped_at is None
    assert c.explanation == EXPLANATION and c.explanation_source == "model"
    assert c.indicator is not None and c.indicator.id == "unemployment_rate"
    assert c.alternatives == ["youth_unemployment_rate"]
    assert c.data is not None and c.data.places == ["IT"] and c.data.rows == 9
    assert c.notes == []
    assert [r.op for r in c.operations] == ["change"] and c.answer == [0]
    assert c.operations[0].value == pytest.approx(-4.2)
    # The chart's series is the one the change read: the claim's place, every year.
    assert c.series is not None and (c.series.geo, c.series.frequency) == ("IT", "annual")
    assert {p.period: p.value for p in c.series.points} == UNEMPLOYMENT_IT
    assert [str(m.step) for m in c.models] == ["match", "plan", "explain"]
    assert [m.provider + "/" + m.model for m in out.models] == ["fake/fake-model"]
    assert not out.retryable
    assert out.versions.catalog == "0.0.1-test" and out.versions.tolerances >= 1
    # The fetch asked Eurostat for the catalog's fixed filters plus the claim's place.
    assert fetcher.calls == [
        ("eurostat", "une_rt_a", {"sex": "T", "age": "Y15-74", "unit": "PC_ACT", "geo": "IT"})
    ]


async def test_steps_summaries_name_what_happened() -> None:
    script = [extraction(claim_json()), match_answer(), plan_answer(), explain_answer()]
    _, events, _, _ = await run(script)
    summaries = {str(e.step): e.summary for e in events if e.event == "step_done"}
    assert summaries["extract"] == "Found 1 claim."
    assert summaries["match"] == "Matched Unemployment rate (eurostat une_rt_a)."
    assert summaries["fetch"] == "Fetched 9 rows, 2015 to 2023."
    assert summaries["plan"] == "Planned change."
    assert summaries["execute"] == (
        "Ran 1 operation; recomputed 36 time windows; 2 framing checks, none flagged."
    )
    assert summaries["verdict"].startswith("supported")
    assert next(e for e in events if e.step is Step.MATCH and e.event == "step_done").models == [
        "fake/fake-model"
    ]


# 2015 is a spike: the fall from it to 2023 is right, but nearby windows mostly rise.
SPIKE = {
    "2013": 7.0, "2014": 7.5, "2015": 11.9, "2016": 8.0, "2017": 7.9, "2018": 8.1,
    "2019": 8.3, "2020": 8.4, "2021": 8.2, "2022": 8.0, "2023": 7.9,
}  # fmt: skip


async def test_a_fall_from_a_spike_holds_but_the_framing_matters() -> None:
    explained = explain_answer("Unemployment fell from 11.9% in 2015 to 7.9% in 2023.")
    script = [extraction(claim_json()), match_answer(), plan_answer(), explained]
    out, events, _, _ = await run(script, FakeFetcher(rows=observations({"IT": SPIKE})))
    [c] = out.claims
    assert c.sweep is not None
    assert (c.sweep.claim_start, c.sweep.claim_end, c.sweep.windows) == ("2015", "2023", 55)
    # Of 15 nearby windows, the fall shows from 2015 (3) and from 2016 to 2023 (1).
    assert (c.sweep.counted, c.sweep.held) == (15, 4)
    assert c.verdict.label is Label.SUPPORTED_FRAMING_MATTERS
    assert c.verdict.window_share == pytest.approx(4 / 15)
    # And 2015 is a peak that carries the fall: from the usual level around it, it is a rise.
    assert c.changepoints is not None
    assert [(f.end, f.period, f.why) for f in c.changepoints.flags] == [("start", "2015", "peak")]
    assert c.verdict.reason == (
        "Holds within tolerance, but the fall shows in only 27% of nearby time windows; it "
        "starts at a peak (2015): from the usual level around then, 7.7, the change is +0.2 "
        "percentage points rather than -4 percentage points."
    )
    summaries = {str(e.step): e.summary for e in events if e.event == "step_done"}
    assert summaries["execute"] == (
        "Ran 1 operation; recomputed 55 time windows; 2 framing checks, 1 flagged."
    )
    # The start on a peak is the one flagged framing check; the points check passes.
    assert [(ch.kind, ch.flagged) for ch in c.distortion_checks] == [
        ("endpoints", True),
        ("points", False),
    ]


async def test_a_steady_fall_is_swept_and_stays_supported() -> None:
    out, _, _, _ = await run(happy_script())
    [c] = out.claims
    assert c.sweep is not None and c.sweep.share == 1.0
    assert c.verdict.window_share == 1.0 and c.verdict.label is Label.SUPPORTED
    assert c.changepoints is not None and c.changepoints.flags == []


async def test_no_claim_found() -> None:
    out, events, calls, fetcher = await run([extraction()])
    assert out.claims == [] and out.notes == [NO_CLAIM]
    assert done(events) == [("extract", "cant_check")]
    assert events[-1].summary == "Found no claim with a number in it."
    assert calls == 1 and fetcher.calls == []


async def test_two_claims_are_checked_in_order() -> None:
    second = claim_json(quote="unemployment rate fell 4 points")
    script = [
        extraction(claim_json(), second),
        match_answer(), plan_answer(), explain_answer(),
        match_answer(), plan_answer(), explain_answer(),
    ]  # fmt: skip
    out, events, calls, _ = await run(script)
    assert [c.index for c in out.claims] == [0, 1] and calls == 7
    assert [e.claim for e in events if e.event == "step_done"][-1] == 1
    assert events[1].summary == "Found 2 claims."


async def test_no_match_stops_the_claim() -> None:
    out, events, calls, fetcher = await run([extraction(claim_json()), match_answer(None)])
    [c] = out.claims
    assert c.verdict.label is Label.CANT_CHECK and c.indicator is None
    assert done(events)[-1] == ("match", "cant_check")
    assert c.stopped_at is Step.MATCH
    assert c.verdict.reason == NO_MATCH
    assert c.explanation == ""  # the page already shows the reason; "Why" has nothing to add
    assert 1 <= len(c.suggestions) <= 3 and all(s.name for s in c.suggestions)
    assert calls == 2 and fetcher.calls == []


async def test_a_claim_with_no_place_cannot_be_fetched() -> None:
    out, events, _, fetcher = await run([extraction(claim_json(geo=None)), match_answer()])
    assert out.claims[0].verdict.reason == NO_PLACE
    assert out.claims[0].stopped_at is Step.FETCH
    assert done(events)[-1] == ("fetch", "cant_check") and fetcher.calls == []


async def test_a_place_the_source_has_no_code_for() -> None:
    script = [extraction(claim_json(type="compare", peers=["G7"])), match_answer()]
    out, events, _, fetcher = await run(script)
    assert out.claims[0].verdict.reason == "Eurostat has no figures for G7."
    assert done(events)[-1] == ("fetch", "cant_check") and fetcher.calls == []


async def test_source_down_is_retryable() -> None:
    fetcher = FakeFetcher(error=SourceUnavailable("eurostat 503"))
    out, events, _, _ = await run([extraction(claim_json()), match_answer()], fetcher)
    [c] = out.claims
    assert c.retryable and out.retryable
    assert c.verdict.reason == "Eurostat didn't answer just now. Please try again in a few minutes."
    assert done(events)[-1] == ("fetch", "cant_check")


async def test_source_without_the_data_is_not_retryable() -> None:
    fetcher = FakeFetcher(error=SourceNotFound("no such dataset"))
    out, _, _, _ = await run([extraction(claim_json()), match_answer()], fetcher)
    assert not out.retryable
    assert out.claims[0].verdict.reason == "Eurostat couldn't provide the figures."


async def test_no_rows_for_the_claims_place() -> None:
    fetcher = FakeFetcher(rows=observations({"DE": {"2015": 4.6, "2023": 3.0}}))
    out, _, calls, _ = await run([extraction(claim_json()), match_answer()], fetcher)
    assert out.claims[0].verdict.reason == "Eurostat has no Unemployment rate figures for Italy."
    assert out.claims[0].data is not None and out.claims[0].data.places == ["DE"]
    assert calls == 2  # no plan call


async def test_source_codes_are_mapped_both_ways() -> None:
    # The claim says EU; Eurostat is asked for EU27_2020 and its rows come back as EU.
    fetcher = FakeFetcher(rows=observations({"EU27_2020": {"2015": 10.1, "2023": 6.1}}))
    script = [
        extraction(claim_json(geo="EU", quote="unemployment rate fell 4 points")),
        match_answer(), plan_answer(geo="EU"), explain_answer("It fell 4 points."),
    ]  # fmt: skip
    out, _, _, _ = await run(script, fetcher)
    [c] = out.claims
    assert fetcher.calls[0][2]["geo"] == "EU27_2020"
    assert c.data is not None and c.data.places == ["EU"]
    assert {p.geo for p in c.operations[0].inputs} == {"EU"}
    assert c.verdict.label is Label.SUPPORTED


async def test_an_invalid_plan_twice_is_cant_check() -> None:
    bad = reply({"calls": [], "answer": [], "reason": "Nothing to do."})
    out, events, calls, _ = await run([extraction(claim_json()), match_answer(), bad, bad])
    [c] = out.claims
    assert c.verdict.reason == PLAN_FAILED
    assert done(events)[-1] == ("plan", "cant_check") and calls == 4
    assert events[-1].models == ["fake/fake-model", "fake/fake-model"]
    assert c.notes and all(n.startswith("Plan rejected: ") for n in c.notes)
    assert c.retryable  # the model may get it right next time: not cached


async def test_an_unsupported_claim_type_is_not_retryable() -> None:
    script = [extraction(claim_json(type="record", value=None)), match_answer()]
    out, events, calls, _ = await run(script)
    [c] = out.claims
    assert c.verdict.reason == unsupported_reason(AssertionType.RECORD)
    assert not c.retryable and calls == 2  # no plan call
    assert c.stopped_at is Step.PLAN
    assert events[-1].models == []


async def test_an_op_error_is_cant_check_with_the_records_so_far() -> None:
    rows = observations({"IT": {"2015": 11.9, "2023": 7.7}}) + observations({"IT": {"2023": 7.8}})
    script = [extraction(claim_json()), match_answer(), plan_answer()]
    out, events, _, _ = await run(script, FakeFetcher(rows=rows))
    assert "two values for 2023" in out.claims[0].verdict.reason
    assert done(events)[-1] == ("execute", "cant_check")


async def test_a_cant_check_verdict_is_explained_by_code() -> None:
    script = [
        extraction(claim_json(value=None, direction=None)), match_answer(), plan_answer(),
    ]  # fmt: skip
    out, events, calls, _ = await run(script)
    [c] = out.claims
    assert c.verdict.label is Label.CANT_CHECK and c.explanation_source == "template"
    assert done(events)[-2:] == [("verdict", "cant_check"), ("explain", "ok")]
    assert calls == 3  # no explain call


async def test_explain_out_of_providers_falls_back_to_the_template() -> None:
    script: Script = [
        extraction(claim_json()), match_answer(), plan_answer(), ProviderUnavailable("down"),
    ]  # fmt: skip
    out, events, _, _ = await run(script)
    [c] = out.claims
    assert c.verdict.label is Label.SUPPORTED and c.explanation_source == "template"
    assert events[-1].summary == "No model available; explained by code."


async def test_an_invented_number_twice_falls_back_to_the_template() -> None:
    # 35% would pass: the points check computed the fall in percent (-35.3%).
    invented = explain_answer("Unemployment fell by 61% since 2015.")
    script = [extraction(claim_json()), match_answer(), plan_answer(), invented, invented]
    out, events, _, _ = await run(script)
    assert out.claims[0].explanation_source == "template"
    assert "61" not in out.claims[0].explanation
    assert "numbers not in the results" in events[-1].summary


async def test_router_out_of_providers_in_extraction_propagates() -> None:
    with pytest.raises(RouterError):
        await run([ProviderUnavailable("down")])
