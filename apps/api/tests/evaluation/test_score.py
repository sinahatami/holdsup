"""Scoring: what each step gets credit for, which step a wrong verdict is blamed on, and what
leaves the figures (an outage is not a wrong answer)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace

import pytest
from scripts.evaluation.benchmark import LabelledClaim
from scripts.evaluation.meter import Call
from scripts.evaluation.score import (
    MISSED,
    ClaimOutcome,
    TextOutcome,
    not_run,
    score_text,
    summarize,
)

from holdsup.pipeline.result import ClaimResult
from holdsup.pipeline.trace import Step
from holdsup.verdict import Label
from tests.evaluation.helpers import label, output, result, spec, text

TOP8 = {0: ["unemployment_rate_monthly", "unemployment_rate_ilo"]}


def score(
    expected: LabelledClaim,
    *results: ClaimResult,
    retrieval: Mapping[int, Sequence[str]] = TOP8,
) -> TextOutcome:
    item = text("t1", "x", expected)
    return score_text(item, output(*results), retrieval, seconds=2.0, model_calls=4)


def only_outcome(outcome: TextOutcome) -> ClaimOutcome:
    [one] = outcome.outcomes
    return one


def test_a_claim_that_goes_right_everywhere_gets_credit_at_every_step() -> None:
    one = only_outcome(score(label(), result()))

    assert (one.found, one.geo_ok, one.start_ok, one.end_ok) == (True, True, True, True)
    assert (one.match_ok, one.in_top8) == (True, True)
    assert (one.verdict, one.verdict_ok, one.failed_step) == ("supported", True, None)
    assert one.explanation == "passed" and one.status == "scored"
    assert "because of the numbers" in one.reason


def test_a_labelled_claim_the_extractor_never_found_is_a_wrong_verdict_at_extraction() -> None:
    outcome = score(label(), result(spec("something unrelated entirely")))
    one = only_outcome(outcome)

    assert (one.found, one.verdict, one.verdict_ok, one.failed_step) == (
        False,
        MISSED,
        False,
        "extract",
    )
    assert (outcome.extracted, outcome.linked) == (1, 0)


def test_a_wrong_window_is_blamed_on_extraction_only_when_the_verdict_is_wrong_too() -> None:
    wrong_window = spec(start="2010", end="2023")

    right_anyway = only_outcome(score(label(), result(wrong_window)))
    wrong = only_outcome(score(label(), result(wrong_window, got=Label.NOT_SUPPORTED)))

    assert right_anyway.start_ok is False and right_anyway.end_ok is True
    assert right_anyway.verdict_ok is True and right_anyway.failed_step is None
    assert wrong.failed_step == "extract"


def test_a_wrong_statistic_is_blamed_on_matching() -> None:
    one = only_outcome(
        score(label(), result(got=Label.NOT_SUPPORTED, indicator="unemployment_rate_ilo"))
    )

    assert (one.match_ok, one.in_top8, one.failed_step) == (False, True, "match")


def test_no_match_for_a_claim_that_has_a_statistic_is_a_matching_failure() -> None:
    one = only_outcome(
        score(label(), result(got=Label.CANT_CHECK, indicator=None, stopped_at=Step.MATCH))
    )

    assert (one.indicator, one.match_ok, one.failed_step) == (None, False, "match")


def test_no_statistic_for_a_claim_the_catalog_cannot_check_is_right() -> None:
    cannot = label(indicator=None, expected=Label.CANT_CHECK)
    one = only_outcome(
        score(cannot, result(got=Label.CANT_CHECK, indicator=None, stopped_at=Step.MATCH))
    )

    assert (one.match_ok, one.in_top8, one.verdict_ok, one.failed_step) == (True, None, True, None)


def test_matching_something_for_a_claim_with_no_statistic_is_a_matching_failure() -> None:
    cannot = label(indicator=None, expected=Label.CANT_CHECK)
    one = only_outcome(score(cannot, result(got=Label.SUPPORTED)))

    assert (one.match_ok, one.failed_step) == (False, "match")


@pytest.mark.parametrize("stopped", [Step.FETCH, Step.PLAN, Step.EXECUTE])
def test_a_claim_that_stops_after_the_right_match_is_blamed_on_the_step_it_stopped_at(
    stopped: Step,
) -> None:
    one = only_outcome(score(label(), result(got=Label.CANT_CHECK, stopped_at=stopped)))

    assert one.failed_step == str(stopped) and one.stopped_at == str(stopped)


def test_a_wrong_label_after_everything_else_went_right_is_blamed_on_the_verdict() -> None:
    one = only_outcome(score(label(), result(got=Label.PARTLY_SUPPORTED)))

    assert (one.verdict_ok, one.failed_step) == (False, "verdict")


def test_stopping_at_the_right_step_for_a_claim_labelled_cant_check_is_right() -> None:
    stale = label(expected=Label.CANT_CHECK)
    one = only_outcome(score(stale, result(got=Label.CANT_CHECK, stopped_at=Step.FETCH)))

    assert (one.verdict_ok, one.failed_step) == (True, None)


def test_a_source_that_did_not_answer_is_left_out_of_the_verdict_but_not_of_matching() -> None:
    down = result(got=Label.CANT_CHECK, stopped_at=Step.FETCH, retryable=True)
    one = only_outcome(score(label(), down))

    assert one.status == "verdict_unavailable" and one.found and one.match_ok is True
    assert (one.verdict, one.verdict_ok, one.failed_step) == (None, None, None)


@pytest.mark.parametrize(
    ("explained", "state"),
    [("model", "passed"), ("template", "rejected"), ("none", "not_asked")],
)
def test_an_explanation_passes_when_code_let_the_models_numbers_through(
    explained: str, state: str
) -> None:
    assert only_outcome(score(label(), result(explained=explained))).explanation == state


def test_a_text_the_router_could_not_serve_runs_no_step() -> None:
    item = text("t1", "x", label(), label("another claim"))
    outcome = not_run(item, "router: no provider available", 1.5, 3)

    assert outcome.error and outcome.labelled == 2 and outcome.model_calls == 3
    assert {o.status for o in outcome.outcomes} == {"not_run"}
    assert {o.found for o in outcome.outcomes} == {False}


# --- totals ---------------------------------------------------------------------------------


def call(step: str = "extract", *, ok: bool = True, ms: float = 100.0, tokens: int = 10) -> Call:
    return Call(step, "groq", "gpt", ok, ms, prompt_tokens=tokens, completion_tokens=tokens)


def two_texts() -> list[TextOutcome]:
    """Four labelled claims: right; wrong verdict (statistic); missed; and an extra claim."""
    first = text(
        "a", "x", label("fell in 2015"), label("rose in 2020", expected=Label.NOT_SUPPORTED)
    )
    second = text(
        "b",
        "y",
        label("debt grew in 2013", expected=Label.NOT_SUPPORTED),
        label("exports halved", expected=Label.PARTLY_SUPPORTED),
    )
    return [
        score_text(
            first,
            output(
                result(spec("fell in 2015"), index=0),
                result(
                    spec("rose in 2020"),
                    got=Label.SUPPORTED,
                    indicator="unemployment_rate_ilo",
                    index=1,
                ),
            ),
            {0: ["unemployment_rate_monthly"], 1: ["unemployment_rate_monthly"]},
            seconds=3.0,
            model_calls=8,
        ),
        score_text(
            second,
            output(result(spec("debt grew in 2013"), got=Label.SUPPORTED, explained="template")),
            {0: ["unemployment_rate_monthly"]},
            seconds=5.0,
            model_calls=4,
        ),
    ]


def test_the_totals_count_each_step_on_the_claims_that_reached_it() -> None:
    m = summarize(two_texts(), [])

    assert (m.texts, m.labelled_claims, m.extracted_claims) == (2, 4, 3)
    e = m.extraction
    assert (e.recall.hits, e.recall.total) == (3, 4)  # "exports halved" was never found
    assert (e.precision.hits, e.precision.total) == (3, 3)
    assert (e.geo.rate, e.window.rate) == (1.0, 1.0)
    assert (m.matching.top1.hits, m.matching.top1.total) == (2, 3)  # one is the wrong statistic
    assert (m.matching.recall_at_8.hits, m.matching.recall_at_8.total) == (3, 3)
    v = m.verdict
    assert (v.accuracy.hits, v.accuracy.total) == (1, 4)  # the missed claim is wrong
    assert (v.accuracy_given_found.hits, v.accuracy_given_found.total) == (1, 3)
    assert (m.explanation.pass_rate.hits, m.explanation.pass_rate.total) == (2, 3)
    assert m.failures == {"match": 1, "verdict": 1, "extract": 1}


def test_the_confusion_matrix_has_a_column_for_missed_claims() -> None:
    v = summarize(two_texts(), []).verdict

    assert v.labels == [*[str(label) for label in Label], MISSED]
    assert v.confusion["supported"]["supported"] == 1
    assert v.confusion["not_supported"]["supported"] == 2
    assert v.confusion["supported"]["not_supported"] == 0
    assert v.confusion["partly_supported"][MISSED] == 1
    assert sum(sum(row.values()) for row in v.confusion.values()) == 4
    assert (v.per_label["supported"].hits, v.per_label["supported"].total) == (1, 1)
    assert (v.per_label["not_supported"].hits, v.per_label["not_supported"].total) == (0, 2)
    assert v.per_label["cant_check"].rate is None  # nothing was labelled cant_check


def test_an_outage_is_counted_and_left_out_rather_than_scored_as_wrong() -> None:
    down = result(got=Label.CANT_CHECK, stopped_at=Step.FETCH, retryable=True)
    texts = [
        score_text(text("a", "x", label()), output(result()), TOP8, seconds=1, model_calls=4),
        score_text(text("b", "y", label()), output(down), TOP8, seconds=1, model_calls=4),
        not_run(text("c", "z", label(), label("other")), "router: out", 1, 1),
    ]

    m = summarize(texts, [])

    assert (m.verdict.accuracy.hits, m.verdict.accuracy.total) == (1, 1)
    assert m.excluded.texts_not_run == 1
    assert (m.excluded.claims_not_run, m.excluded.claims_verdict_unavailable) == (2, 1)
    assert m.excluded.share == 0.75
    # The claim whose source was down still counts for extraction and matching ...
    assert m.extraction.recall.total == 2 and m.matching.top1.total == 2
    # ... and the text nothing could run for counts for none of them.
    assert m.extracted_claims == 2


def test_cost_per_claim_and_per_text_with_the_calls_of_each_step_and_provider() -> None:
    calls = [call("extract"), call("extract", ok=False), call("match", ms=300.0), call("match")]
    m = summarize(two_texts(), calls, series_requests=4, series_fetches=3)
    c = m.cost

    assert (c.model_calls, c.failed_calls, c.calls_per_claim) == (4, 1, 1.0)
    assert (c.prompt_tokens, c.completion_tokens) == (40, 40)
    assert (c.seconds, c.seconds_per_claim) == (8.0, 2.0)
    assert (c.seconds_p50_per_text, c.seconds_p95_per_text) == (3.0, 5.0)
    assert (c.series_requests, c.series_cache_hits, c.series_cache_hit_rate) == (4, 1, 0.25)
    by = {(s.step, s.provider): s for s in c.by_step_provider}
    assert (by["extract", "groq"].calls, by["extract", "groq"].failed) == (2, 1)
    assert by["match", "groq"].mean_latency_ms == 200.0


def test_the_providers_that_reached_their_daily_limit_are_named_once() -> None:
    spent = Call("match", "groq", "gpt", False, 50.0, error="RateLimited", daily_limit=True)
    calls = [spent, replace(spent, step="plan"), call("match", ok=False), call("match")]

    m = summarize(two_texts(), calls)

    assert m.cost.daily_limited == ["groq"]
    assert summarize(two_texts(), [call(ok=False)]).cost.daily_limited == []


def test_an_empty_run_has_nothing_to_report_rather_than_a_zero() -> None:
    m = summarize([], [])

    assert m.verdict.accuracy.rate is None and m.extraction.recall.rate is None
    assert (m.cost.calls_per_claim, m.cost.seconds_p95_per_text) == (None, None)
    assert (m.cost.series_cache_hit_rate, m.excluded.share) == (None, None)


# --- confidence (P4.5) -----------------------------------------------------------------------


def scored(p: float | None, *, abstain: bool, right: bool, i: int) -> TextOutcome:
    from holdsup.ml.confidence import Confidence, Signals

    claim = result(got=Label.SUPPORTED if right else Label.NOT_SUPPORTED)
    claim.confidence = Confidence(
        signals=Signals(rerank_margin=0.3), probability=p, abstain=abstain
    )
    return score_text(text(f"t{i}", "x", label()), output(claim), TOP8, seconds=1.0, model_calls=4)


def test_a_claim_keeps_the_confidence_it_was_given_for_training_and_for_the_figures() -> None:
    one = only_outcome(scored(0.4, abstain=True, right=False, i=0))
    assert one.confidence is not None and one.confidence.signals.rerank_margin == 0.3


def test_the_verdicts_answered_and_held_back_are_scored_apart() -> None:
    texts = [
        scored(0.9, abstain=False, right=True, i=0),
        scored(0.8, abstain=False, right=True, i=1),
        scored(0.7, abstain=False, right=False, i=2),
        scored(0.3, abstain=True, right=False, i=3),
        scored(None, abstain=False, right=True, i=4),  # signals only: no model was loaded
        score(label(), result(got=Label.CANT_CHECK, stopped_at=Step.MATCH, indicator=None)),
    ]
    c = summarize(texts, []).confidence
    assert c is not None and c.scored == 4
    assert (c.abstained.hits, c.abstained.total) == (1, 4)
    assert (c.answered_accuracy.hits, c.answered_accuracy.total) == (2, 3)
    assert (c.abstained_accuracy.hits, c.abstained_accuracy.total) == (0, 1)
