"""Reading the benchmark, and the grouped folds."""

from collections import Counter

import pytest

from reranker.benchmark import Claim, dev
from reranker.folds import assign_folds
from tests.helpers import DEBT, UNEMPLOYMENT


def test_claims_are_keyed_from_1_and_no_split_counts_as_dev(claims: list[Claim]) -> None:
    by_key = {c.key: c for c in claims}
    assert by_key["d2#2"].quote == "Spain's debt was 120% of GDP in 2020"
    assert by_key["d2#2"].split == "dev" and by_key["d2#2"].text_id == "d2"
    assert by_key["d2#2"].text.startswith("Spain's youth unemployment rate")
    assert by_key["t1#1"].split == "test"
    assert [c.key for c in dev(claims)] == ["d1#1", "d2#1", "d2#2", "d3#1", "d4#1"]


def test_a_group_is_the_statistic_and_place_or_the_claim_alone(claims: list[Claim]) -> None:
    by_key = {c.key: c for c in claims}
    assert by_key["d1#1"].group == f"{UNEMPLOYMENT}@IT"
    assert by_key["d2#2"].group == f"{DEBT}@ES"
    assert by_key["d3#1"].group == "d3#1"  # nothing in the catalog: its own group


GROUPS = ["a"] * 5 + ["b"] * 3 + ["c"] * 3 + ["d"] * 2 + ["e", "f", "g", "h"]


def test_every_group_lands_in_one_fold_and_folds_are_balanced() -> None:
    folds = assign_folds(GROUPS, 3, seed=13)
    assert set(folds) == set(GROUPS)
    sizes = Counter()  # type: Counter[int]
    for g in GROUPS:
        sizes[folds[g]] += 1
    assert set(sizes) == {0, 1, 2}
    assert max(sizes.values()) - min(sizes.values()) <= 1


def test_a_seed_always_gives_the_same_split() -> None:
    assert assign_folds(GROUPS, 3, seed=13) == assign_folds(list(reversed(GROUPS)), 3, seed=13)


def test_too_few_groups_or_folds_is_an_error() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        assign_folds(GROUPS, 1, seed=1)
    with pytest.raises(ValueError, match="cannot fill"):
        assign_folds(["a", "a", "b"], 3, seed=1)
