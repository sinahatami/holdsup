"""The reranker in matching: both branches of the skip-the-model rule (P4.4), with a reranker
that answers from a table, a fake router and the test catalog. No model, no network."""

import pytest

from holdsup.catalog.index import IndicatorHit, _hit
from holdsup.pipeline.match import SKIP_MARGIN, Ranked, rerank
from holdsup.router.client import ChatResponse
from tests.ml.fakes import FakeReranker
from tests.pipeline.test_match import CATALOG, answer, claim, matcher

COVERING_IT = ["youth_unemployment_rate", "unemployment_rate", "hicp_inflation"]


async def test_a_clear_reranker_pick_skips_the_model() -> None:
    m, client = matcher([])  # no scripted reply: a model call would fail the test
    reranker = FakeReranker(
        CATALOG, {"youth_unemployment_rate": 0.97, "unemployment_rate": 0.2, "hicp_inflation": 0.01}
    )
    m.reranker = reranker

    result = await m.match(claim())

    assert client.calls == []
    assert (result.status, result.indicator_id, result.confidence) == (
        "matched",
        "youth_unemployment_rate",
        "high",
    )
    assert result.skipped_model and result.providers == [] and result.tool_calls == []
    assert (result.reranker, result.margin) == ("fake/reranker@0000000", 0.77)
    assert [(c.id, c.rerank) for c in result.candidates] == [
        ("youth_unemployment_rate", 0.97),
        ("unemployment_rate", 0.2),
        ("hicp_inflation", 0.01),
    ]
    assert result.alternatives == []
    assert "Youth unemployment rate" in result.reason and "margin 0.77" in result.reason
    assert result.notes == ["matched by the reranker alone: margin 0.77 is at least 0.50"]
    # The reranker reads the claim's sentence, as it was trained to.
    assert reranker.queries == [claim().quote]


async def test_a_close_call_goes_to_the_model_in_the_reranker_s_order() -> None:
    m, client = matcher([ChatResponse(content=answer("youth_unemployment_rate"))])
    m.reranker = FakeReranker(
        CATALOG, {"unemployment_rate": 0.6, "youth_unemployment_rate": 0.5, "hicp_inflation": 0.3}
    )

    result = await m.match(claim())

    # The model decides, and it may disagree with the reranker's first.
    assert len(client.calls) == 1
    assert (result.status, result.indicator_id) == ("matched", "youth_unemployment_rate")
    assert not result.skipped_model and result.providers == ["fake"]
    assert (result.reranker, result.margin) == ("fake/reranker@0000000", 0.1)
    assert [c.id for c in result.candidates] == [
        "unemployment_rate",
        "youth_unemployment_rate",
        "hicp_inflation",
    ]
    [(_, request)] = client.calls
    user = str(request.messages[1]["content"])
    listed = [user.index(f"- {i}:") for i in ("unemployment_rate", "youth_unemployment_rate")]
    assert listed == sorted(listed) and user.index("- hicp_inflation:") > listed[-1]


async def test_a_margin_exactly_at_the_threshold_skips() -> None:
    m, client = matcher([])
    m.reranker = FakeReranker(CATALOG, {"unemployment_rate": 0.75, "youth_unemployment_rate": 0.25})
    result = await m.match(claim("unemployment rate"))
    assert client.calls == [] and result.indicator_id == "unemployment_rate"
    assert result.margin == SKIP_MARGIN == 0.5


async def test_a_stricter_threshold_asks_the_model() -> None:
    m, client = matcher([ChatResponse(content=answer("youth_unemployment_rate"))])
    m.reranker = FakeReranker(CATALOG, {"youth_unemployment_rate": 0.97})
    m.skip_margin = 0.99
    result = await m.match(claim())
    assert len(client.calls) == 1 and not result.skipped_model and result.margin == 0.97


async def test_a_model_turning_down_the_reranker_s_first_is_still_cant_check() -> None:
    m, _ = matcher([ChatResponse(content=answer(None, "low"))])
    m.reranker = FakeReranker(CATALOG, {"youth_unemployment_rate": 0.4, "unemployment_rate": 0.3})
    result = await m.match(claim())
    assert result.status == "cant_check" and result.reranker == "fake/reranker@0000000"


async def test_no_covering_candidate_never_reaches_the_reranker() -> None:
    m, client = matcher([])
    reranker = FakeReranker(CATALOG, {"life_expectancy": 0.99})
    m.reranker = reranker
    result = await m.match(claim(geo="XX"))
    assert result.status == "cant_check" and result.reranker is None
    assert reranker.queries == [] and client.calls == []


async def test_without_a_reranker_the_search_order_reaches_the_model() -> None:
    m, _ = matcher([ChatResponse(content=answer("youth_unemployment_rate"))])
    result = await m.match(claim())
    assert result.reranker is None and result.margin is None and not result.skipped_model
    assert all(c.rerank is None for c in result.candidates)


# --- ranking and margin ------------------------------------------------------------------


def hits(*ids: str) -> list[IndicatorHit]:
    return [_hit(CATALOG.get(i), 1.0 - n / 10) for n, i in enumerate(ids)]


async def test_equal_probabilities_keep_the_search_order() -> None:
    ranked = await rerank(
        FakeReranker(CATALOG, {"hicp_inflation": 0.9}), "q", hits(*COVERING_IT), CATALOG
    )
    assert [h.id for h in ranked.hits] == ["hicp_inflation", *COVERING_IT[:2]]
    assert ranked.probabilities == [0.9, 0.0, 0.0] and ranked.model == "fake/reranker@0000000"


@pytest.mark.parametrize(
    ("probabilities", "margin"), [([0.9, 0.3, 0.1], 0.6), ([0.7], 0.7), ([], 0.0)]
)
def test_the_margin_is_the_first_minus_the_second(
    probabilities: list[float], margin: float
) -> None:
    ranked = Ranked("m", hits(*COVERING_IT[: len(probabilities)]), probabilities)
    assert ranked.margin == pytest.approx(margin)
