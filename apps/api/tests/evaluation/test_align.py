"""Pairing the extractor's claims with the labelled ones."""

import pytest
from scripts.evaluation.align import (
    align,
    end_ok,
    geo_ok,
    overlap,
    period_ok,
    start_ok,
    words,
)

from tests.evaluation.helpers import label, spec


def test_stop_words_do_not_count_as_overlap() -> None:
    assert words("The rate is 7.7% in 2023") == {"rate", "7.7", "2023"}
    assert overlap("in the of", "to a an") == 0.0


def test_a_whole_sentence_covers_a_short_labelled_fragment() -> None:
    sentence = "Since I took office, youth unemployment has fallen 12 points, from 44% to 32%"

    assert overlap("youth unemployment has fallen 12 points", sentence) == 1.0
    assert overlap("from 44% to 32%", sentence) == 1.0
    assert overlap("Italy's public debt is 133% of GDP", sentence) < 0.5


@pytest.mark.parametrize(
    ("expected", "got", "ok"),
    [
        ("2015", "2015", True),
        ("2015", "2015-03", True),  # a bare year takes any month of it
        ("2015", "2016", False),
        ("2014-02", "2014-02", True),
        ("2014-02", "2014-03", False),  # a month must match exactly
        ("2014-02", "2014", False),
        ("latest", "latest", True),
        ("latest", "2025", False),
        ("2015", None, False),
    ],
)
def test_periods(expected: str, got: str | None, ok: bool) -> None:
    assert period_ok(expected, got) is ok


def test_a_level_claim_may_leave_its_start_empty() -> None:
    level = label(window=("2013", "2013"))
    said = spec(start=None, end="2013")

    assert start_ok(level, said) and end_ok(level, said)
    assert not start_ok(label(window=("2012", "2013")), said)


def test_geo_must_match_exactly() -> None:
    assert geo_ok(label(geo="IT"), spec(geo="IT"))
    assert not geo_ok(label(geo="IT"), spec(geo="FR"))
    assert geo_ok(label(geo=None), spec(geo=None))


def test_claims_are_paired_whatever_their_order() -> None:
    labelled = [label("youth unemployment was 29% in 2011"), label("debt hit 132.6% in 2013")]
    extracted = [spec("debt hit 132.6% in 2013"), spec("youth unemployment was 29% in 2011")]

    links = align(labelled, extracted)

    assert [(link.label, link.extracted) for link in links] == [(0, 1), (1, 0)]


def test_a_claim_nobody_labelled_and_a_labelled_claim_nobody_extracted_stay_unpaired() -> None:
    labelled = [label("unemployment fell from 11.9% in 2015 to 7.7% in 2023")]
    extracted = [spec("debt hit 132.6% in 2013"), spec("ice cream sales doubled")]

    assert align(labelled, extracted) == []


def test_two_labelled_claims_cannot_share_one_extracted_claim() -> None:
    labelled = [label("debt hit 132.6% in 2013"), label("up from 127% in 2012")]
    merged = [spec("debt hit 132.6% in 2013, up from 127% in 2012")]

    links = align(labelled, merged)

    assert len(links) == 1  # the other one was not extracted: it gets no verdict


def test_a_tie_goes_to_the_claim_that_agrees_on_place_and_window() -> None:
    labelled = [label("youth unemployment fell 12 points", window=("2014-02", "latest"))]
    wrong = spec("youth unemployment fell 12 points", start="2010", end="2012")
    right = spec("youth unemployment fell 12 points", start="2014-02", end="latest")

    [link] = align(labelled, [wrong, right])

    assert link.extracted == 1 and link.overlap == 1.0
