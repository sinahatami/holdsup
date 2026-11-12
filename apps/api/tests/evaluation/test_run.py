"""Whole runs: the real pipeline with a scripted provider and recorded source data, scored."""

import pytest
from scripts.evaluation.run import Rig, evaluate, only_provider

from holdsup.adapters.base import FetchedSeries, Filters, SourceUnavailable
from holdsup.catalog.index import IndicatorHit
from holdsup.router.errors import ProviderUnavailable
from holdsup.verdict import Label
from tests.evaluation.helpers import FALL, fall_claim, fall_script, label, make_rig, text
from tests.pipeline.test_regressions import extraction, match
from tests.router.fakes import config, provider


async def test_a_text_is_checked_and_scored_step_by_step() -> None:
    rig, _, meter = make_rig(fall_script())

    [outcome] = await evaluate(rig, [text()])

    [one] = outcome.outcomes
    assert outcome.error is None and (outcome.extracted, outcome.linked) == (1, 1)
    assert (one.found, one.geo_ok, one.start_ok, one.end_ok) == (True, True, True, True)
    assert (one.indicator, one.match_ok, one.in_top8) == ("unemployment_rate_monthly", True, True)
    assert (one.verdict, one.verdict_ok, one.failed_step) == ("supported", True, None)
    assert one.explanation == "passed"
    # Each model call is counted against the step that made it.
    assert [c.step for c in meter.calls] == ["extract", "match", "plan", "explain"]
    assert outcome.model_calls == 4 and outcome.seconds >= 0
    assert sum(c.prompt_tokens for c in meter.calls) == 40


async def test_progress_says_how_each_text_went() -> None:
    rig, _, _ = make_rig(fall_script())
    lines: list[str] = []

    await evaluate(rig, [text()], lines.append)

    assert len(lines) == 1
    assert lines[0].startswith("[1/1] r001: 1/1 verdicts right, 4 model calls")


async def test_retrieval_is_the_search_of_the_phrase_the_extractor_read() -> None:
    rig, _, _ = make_rig(fall_script())
    asked: list[tuple[str, int]] = []

    async def recording(phrase: str, k: int) -> list[IndicatorHit]:
        asked.append((phrase, k))
        return await rig.search(phrase, k)

    await evaluate(Rig(rig.pipeline, recording, rig.meter), [text()])

    assert asked == [("unemployment rate", 8)]


async def test_a_claim_with_no_match_is_a_matching_failure_with_a_cant_check_verdict() -> None:
    rig, _, _ = make_rig([extraction(fall_claim()), match(None)])

    [outcome] = await evaluate(rig, [text()])

    [one] = outcome.outcomes
    assert (one.found, one.indicator, one.match_ok) == (True, None, False)
    assert one.verdict == "cant_check" and one.failed_step == "match"
    assert one.stopped_at == "match"


async def test_a_text_with_no_claim_in_it_misses_every_labelledfall_claim() -> None:
    rig, _, _ = make_rig([extraction()])

    [outcome] = await evaluate(rig, [text()])

    [one] = outcome.outcomes
    assert (outcome.extracted, outcome.linked) == (0, 0)
    assert (one.found, one.verdict, one.failed_step) == (False, "missed", "extract")


async def test_a_text_the_router_cannot_serve_is_not_run_and_the_run_goes_on() -> None:
    rig, _, meter = make_rig([], keys=set())

    outcomes = await evaluate(rig, [text("a"), text("b")])

    assert [o.error is not None for o in outcomes] == [True, True]
    assert outcomes[0].error and outcomes[0].error.startswith("router: no provider available")
    assert {o.status for t in outcomes for o in t.outcomes} == {"not_run"}
    assert meter.calls == []


async def test_a_provider_that_fails_everywhere_is_a_router_error_not_a_crash() -> None:
    rig, _, meter = make_rig([ProviderUnavailable("503")])

    [outcome] = await evaluate(rig, [text()])

    assert outcome.error is not None and outcome.model_calls == 1
    assert [c.ok for c in meter.calls] == [False]


class DownFetcher:
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        raise SourceUnavailable("503")


async def test_a_source_that_is_down_leaves_the_verdict_out_but_keeps_the_match() -> None:
    rig, _, _ = make_rig(
        [extraction(fall_claim()), match("unemployment_rate_monthly")], fetcher=DownFetcher()
    )

    [outcome] = await evaluate(rig, [text()])

    [one] = outcome.outcomes
    assert one.status == "verdict_unavailable" and one.match_ok is True
    assert (one.verdict, one.verdict_ok) == (None, None)


class BrokenFetcher:
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries:
        raise RuntimeError("a bug")


async def test_a_bug_stops_the_run_instead_of_being_scored_as_an_answer() -> None:
    rig, _, _ = make_rig(
        [extraction(fall_claim()), match("unemployment_rate_monthly")], fetcher=BrokenFetcher()
    )

    with pytest.raises(RuntimeError, match="a bug"):
        await evaluate(rig, [text()])


async def test_a_label_that_expects_cant_check_is_right_when_the_pipeline_cannot() -> None:
    rig, _, _ = make_rig([extraction(fall_claim()), match(None)])
    cannot = label(indicator=None, expected=Label.CANT_CHECK)

    [outcome] = await evaluate(rig, [text("x", FALL, cannot)])

    [one] = outcome.outcomes
    assert (one.match_ok, one.verdict_ok, one.failed_step) == (True, True, None)


def test_a_per_provider_run_sends_every_step_to_that_provider() -> None:
    cfg = config(
        provider("a"), provider("b"), steps={"extract": ["a", "b"], "match": ["b"], "plan": ["a"]}
    )

    only = only_provider(cfg, "b")

    assert only.steps == {"extract": ("b",), "match": ("b",), "plan": ("b",)}
    assert [p.name for p in only.providers] == ["a", "b"]
    assert cfg.steps["extract"] == ("a", "b")  # the original is untouched


def test_an_unknown_provider_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        only_provider(config(provider("a")), "nope")
