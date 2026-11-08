"""The can't-check topic report: grouping, ranking and what it leaves out."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec
from holdsup.pipeline.result import ClaimResult, IndicatorRef, Suggestion, Versions
from holdsup.service.missing import format_report, summarize, topic_key
from holdsup.service.store.model import CheckResult
from holdsup.verdict.model import Label, Verdict

T0 = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)


def claim(
    phrase: str,
    label: Label = Label.CANT_CHECK,
    *,
    quote: str = "A claim.",
    retryable: bool = False,
    matched: bool = False,
    closest: str | None = None,
) -> ClaimResult:
    spec = ClaimSpec(
        quote=quote, indicator_phrase=phrase, geo="IT", geo_basis=None, peers=[],
        start=None, start_basis=None, end="latest", end_basis=None, speaker=None, said_on=None,
        assertion=Assertion(
            type=AssertionType.LEVEL, value=5, direction=None, unit="%", start_value=None,
            end_value=None,
        ),
    )  # fmt: skip
    return ClaimResult(
        index=0, claim=spec, verdict=Verdict(label=label, reason="r"), explanation="",
        indicator=IndicatorRef(
            id="x", name="X", source="eurostat", source_code="c", unit="%",
            frequency="annual", definition="d",
        ) if matched else None,
        suggestions=[Suggestion(id="s", name=closest)] if closest else [],
        retryable=retryable,
    )  # fmt: skip


def stored(*claims: ClaimResult, age_minutes: int = 0) -> dict[str, Any]:
    result = CheckResult(
        id=uuid4(), text="t", created_at=T0 + timedelta(minutes=age_minutes),
        finished_at=T0 + timedelta(minutes=age_minutes, seconds=9), claims=list(claims),
        versions=Versions(app="0", catalog="0.6.0", tolerances=2), models=[],
    )  # fmt: skip
    return result.model_dump(mode="json")


def test_topic_key_ignores_case_punctuation_and_spacing() -> None:
    assert topic_key("  Gender  pay-gap! ") == "gender pay gap"
    assert topic_key("...") == ""


def test_ranks_cant_check_topics_and_merges_small_variations() -> None:
    results = [
        stored(claim("Gender pay gap", closest="Employment rate"), claim("rent prices")),
        stored(claim("gender pay-gap", quote="Women earn 5% less."), age_minutes=5),
        stored(claim("Gender pay gap", matched=True)),
        stored(claim("unemployment", Label.SUPPORTED)),  # answered: not counted
    ]
    report = summarize(results)
    assert report.checks_read == 4 and report.cant_check == 4
    first, second = report.topics
    assert (first.topic, first.claims, first.checks, first.unmatched) == ("Gender pay gap", 3, 3, 2)
    assert first.closest == "Employment rate"
    assert first.example == "Women earn 5% less."  # the newest check's quote
    assert (second.topic, second.claims) == ("rent prices", 1)


def test_a_passing_outage_is_not_a_missing_topic() -> None:
    report = summarize([stored(claim("unemployment", retryable=True))])
    assert report.topics == [] and report.cant_check == 0


def test_limit_and_ties() -> None:
    results = [stored(claim("b topic")), stored(claim("a topic")), stored(claim("c topic"))]
    report = summarize(results, limit=2)
    assert [t.topic for t in report.topics] == ["a topic", "b topic"]


def test_unreadable_results_are_counted_not_fatal() -> None:
    report = summarize([{"old": "shape"}, stored(claim("rent prices"))])
    assert report.unreadable == 1 and report.checks_read == 1


def test_a_claim_with_no_topic_words_is_skipped() -> None:
    assert summarize([stored(claim("???"))]).topics == []


def test_format_report() -> None:
    text = format_report(summarize([stored(claim("rent prices", quote="x" * 150, closest="HICP"))]))
    assert "1 can't-check claims in 1 finished checks" in text
    assert "  1. rent prices  (1 claim in 1 check)" in text
    assert "no statistic matched: 1 of 1" in text and "closest offered: HICP" in text
    assert "x" * 100 + "…" in text and "x" * 101 not in text
    assert "could not be read" not in text


def test_format_report_pluralises() -> None:
    results = [stored(claim("rent prices")), stored(claim("rent prices"))]
    assert "(2 claims in 2 checks)" in format_report(summarize(results))


def test_format_report_when_empty_or_partly_unreadable() -> None:
    assert "Nothing to add" in format_report(summarize([]))
    text = format_report(summarize([{"old": "shape"}]))
    assert "1 stored results could not be read" in text
