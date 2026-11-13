"""Cross-validation with fake models: who trains on what, and who scores what."""

from collections.abc import Sequence

import pytest

from holdsup.catalog.schema import Catalog
from reranker.benchmark import Claim, parse_claims
from reranker.dataset import Group, Pair, build_groups
from reranker.experiment import BASE, EMBEDDING, RERANKER, agreement, cross_validate, max_logit_diff
from reranker.paraphrase import Paraphrase
from tests.helpers import DEBT, LIFE, UNEMPLOYMENT, YOUTH, FixedSearch, line

STATS = [(UNEMPLOYMENT, "IT"), (UNEMPLOYMENT, "ES"), (YOUTH, "ES"), (DEBT, "FR"), (LIFE, "IT")]


def benchmark() -> list[Claim]:
    lines = [
        line(f"x{n}", [(f"claim {n} about {stat} in {geo}", stat, geo)], "dev")
        for n, (stat, geo) in enumerate(STATS * 2)  # two claims per group
    ]
    return parse_claims([*lines, line("t", [("held out", DEBT, "FR")], "test")])


def groups(catalog: Catalog) -> list[Group]:
    claims = benchmark()
    paraphrases = [
        Paraphrase(claim=c.key, text=f"{c.quote}, reworded", provider="p", model="m")
        for c in claims
        if c.split == "dev"
    ]
    pool = [(UNEMPLOYMENT, 0.9), (YOUTH, 0.8), (DEBT, 0.7), (LIFE, 0.6)]
    return build_groups(claims, paraphrases, catalog, FixedSearch(pool))


class Recorder:
    """A fake fit: remembers the sentences it trained on; its model prefers the last
    candidate (so its order differs from the search's)."""

    def __init__(self) -> None:
        self.trained: list[set[str]] = []

    def __call__(self, pairs: Sequence[Pair]) -> "Reversed":
        self.trained.append({p.query for p in pairs})
        return Reversed()


class Reversed:
    def logits(self, query: str, documents: Sequence[str]) -> list[float]:
        return [float(i) for i in range(len(documents))]


class Flat:
    def logits(self, query: str, documents: Sequence[str]) -> list[float]:
        return [0.0] * len(documents)


def test_no_fold_scores_a_claim_whose_group_it_trained_on(catalog: Catalog) -> None:
    gs = groups(catalog)
    fit = Recorder()
    cv = cross_validate(gs, catalog, fit, k=5, seed=13)
    assert len(fit.trained) == 5 and sum(cv.fold_sizes) == 10
    scored = cv.rows[RERANKER]
    assert sorted(r.claim for r in scored) == sorted(
        g.query.claim.key for g in gs if not g.query.paraphrase
    )
    group_of = {g.query.text: g.query.claim.group for g in gs}
    start = 0
    for trained, size in zip(fit.trained, cv.fold_sizes, strict=True):
        held = {next(g for g in gs if g.query.claim.key == r.claim).query.claim.group
                for r in scored[start : start + size]}  # fmt: skip
        assert not {group_of[q] for q in trained} & held
        start += size


def test_rows_for_every_ranker_on_the_same_candidates(catalog: Catalog) -> None:
    cv = cross_validate(groups(catalog), catalog, Recorder(), k=5, seed=13, base=Flat())
    emb, base, rer = cv.rows[EMBEDDING], cv.rows[BASE], cv.rows[RERANKER]
    assert len(emb) == len(base) == len(rer) == 10
    for e, b, r in zip(emb, base, rer, strict=True):
        assert set(e.ids) == set(b.ids) == set(r.ids)
        assert e.seen == b.seen == r.seen
    assert emb[0].ids == (UNEMPLOYMENT, YOUTH, DEBT, LIFE)  # the search's order
    assert rer[0].ids == (LIFE, DEBT, YOUTH, UNEMPLOYMENT)  # the fake model's
    assert base[0].ids == emb[0].ids  # a flat score keeps the search order


def test_no_base_no_base_rows(catalog: Catalog) -> None:
    assert BASE not in cross_validate(groups(catalog), catalog, Recorder(), k=2, seed=1).rows


def test_a_statistic_is_seen_when_another_group_trained_on_it(catalog: Catalog) -> None:
    cv = cross_validate(groups(catalog), catalog, Recorder(), k=5, seed=13)
    # UNEMPLOYMENT has two places, so some fold trains on one while scoring the other.
    assert any(r.seen for r in cv.rows[RERANKER] if r.gold == UNEMPLOYMENT)
    assert not any(r.seen for r in cv.rows[RERANKER] if r.gold == DEBT)  # one group only


def test_agreement_and_logit_difference() -> None:
    work = [("q", ["a", "b", "c"]), ("q2", ["a", "b"]), ("q3", [])]
    same, worst = agreement(Reversed(), Reversed(), work)
    assert same == 1.0 and worst == 0.0
    same, worst = agreement(Reversed(), Flat(), work)
    # Flat's first is the first, Reversed's the last: only the empty claim agrees.
    assert same == pytest.approx(1 / 3)
    assert worst == pytest.approx(0.380797, abs=1e-6)  # sigmoid(2) - sigmoid(0)
    assert max_logit_diff(Reversed(), Flat(), work) == 2.0
    assert max_logit_diff(Reversed(), Flat(), []) == 0.0
