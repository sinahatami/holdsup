"""Top-1, recall@8, MRR@8 and the margin table, on hand-made rankings."""

import pytest

from reranker.metrics import Ranked, margin_table, rank, reciprocal_rank, sigmoid, summarize


def r(gold: str | None, ids: str, scores: list[float], seen: bool = True) -> Ranked:
    return Ranked("k", gold, tuple(ids), tuple(scores), seen)


def test_rank_orders_by_score_and_keeps_search_order_on_ties() -> None:
    ranked = rank("k", "c", ["a", "b", "c"], [0.2, 0.5, 0.5], seen=False)
    assert ranked.ids == ("b", "c", "a")
    assert ranked.scores == (0.5, 0.5, 0.2)
    assert not ranked.seen


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(r("a", "abc", [3, 2, 1])) == 1.0
    assert reciprocal_rank(r("c", "abc", [3, 2, 1])) == pytest.approx(1 / 3)
    assert reciprocal_rank(r("z", "abc", [3, 2, 1])) == 0.0
    assert reciprocal_rank(r(None, "abc", [3, 2, 1])) == 0.0
    assert reciprocal_rank(r("c", "abc", [3, 2, 1]), k=2) == 0.0


def test_summary_leaves_out_claims_with_no_statistic() -> None:
    rows = [r("a", "ab", [2, 1]), r("b", "ab", [2, 1]), r("z", "ab", [2, 1]), r(None, "ab", [2, 1])]
    s = summarize(rows)
    assert s.claims == 3
    assert s.top1 == pytest.approx(1 / 3)
    assert s.recall_at_8 == pytest.approx(2 / 3)
    assert s.mrr_at_8 == pytest.approx((1 + 0.5 + 0) / 3)
    empty = summarize([r(None, "a", [1])])
    assert empty.claims == 0 and empty.top1 is None and empty.mrr_at_8 is None


def test_margin_is_first_minus_second() -> None:
    assert r("a", "ab", [0.9, 0.3]).margin == pytest.approx(0.6)
    assert r("a", "a", [0.7]).margin == pytest.approx(0.7)
    assert r("a", "", []).margin == 0.0


def test_margin_table_counts_an_answered_claim_with_no_statistic_as_wrong() -> None:
    rows = [
        r("a", "ab", [0.95, 0.05]),  # right, wide margin
        r("b", "ab", [0.90, 0.20]),  # wrong, wide margin
        r(None, "ab", [0.80, 0.10]),  # nothing to find, wide margin: wrong if answered
        r("a", "ab", [0.40, 0.35]),  # right, narrow margin
    ]
    low, high, none = margin_table(rows, [0.05, 0.85, 0.99])
    assert (low.answered, low.correct, low.coverage) == (4, 2, 1.0)
    assert low.accuracy == pytest.approx(0.5)
    assert (high.answered, high.correct, high.accuracy) == (1, 1, 1.0)
    assert (none.answered, none.accuracy, none.coverage) == (0, None, 0.0)
    assert margin_table([], [0.5])[0].coverage == 0.0


def test_sigmoid() -> None:
    assert sigmoid(0) == 0.5
    assert sigmoid(10) > 0.9999 and sigmoid(-10) < 0.0001
