"""Query groups: the pipeline's candidate rule, positives, hard negatives, no-match groups."""

import math
from collections.abc import Sequence

from holdsup.catalog.coverage import covers
from holdsup.catalog.schema import Catalog
from holdsup.pipeline.match.candidates import SEARCH_POOL, TOP_K
from reranker.benchmark import Claim, parse_claims
from reranker.dataset import build_groups, embedding_search, pairs, queries
from reranker.paraphrase import Paraphrase
from tests.helpers import DEBT, EUROSTAT_ONLY, LIFE, UNEMPLOYMENT, YOUTH, FixedSearch, line


def para(claim: str, text: str) -> Paraphrase:
    return Paraphrase(claim=claim, text=text, provider="p", model="m")


def test_queries_are_the_dev_quotes_then_their_paraphrases(claims: list[Claim]) -> None:
    qs = queries(claims, [para("d1#1", "Italian joblessness hit 8% in 2022")])
    assert [q.claim.key for q in qs if not q.paraphrase] == ["d1#1", "d2#1", "d2#2", "d3#1", "d4#1"]
    [p] = [q for q in qs if q.paraphrase]
    assert p.claim.key == "d1#1" and p.text == "Italian joblessness hit 8% in 2022"


def test_candidates_cover_the_place_keep_search_order_and_stop_at_8(catalog: Catalog) -> None:
    us_claim = parse_claims([line("d", [("US life expectancy was 77", LIFE, "US")], "dev")])
    us = [s.id for s in catalog.indicators if covers(s.geo_coverage, "US")]
    assert len(us) > TOP_K
    pool = [(i, 0.9) for i in EUROSTAT_ONLY] + [(i, 0.5 - n / 100) for n, i in enumerate(us)]
    [group] = build_groups(us_claim, [], catalog, FixedSearch(pool))
    assert not set(group.ids) & set(EUROSTAT_ONLY)  # Eurostat does not cover the US
    assert group.ids == tuple(us[:TOP_K])
    assert list(group.similarities) == sorted(group.similarities, reverse=True)


def test_the_labelled_statistic_is_added_for_training_when_search_missed_it(
    claims: list[Claim], catalog: Catalog
) -> None:
    groups = build_groups(claims, [], catalog, FixedSearch([(LIFE, 0.8), (YOUTH, 0.7)]))
    italy = next(g for g in groups if g.query.claim.key == "d1#1")  # labelled UNEMPLOYMENT
    assert italy.ids == (LIFE, YOUTH)
    assert italy.training_ids == (LIFE, YOUTH, UNEMPLOYMENT)
    labels = {p.document: p.label for p in pairs([italy], catalog)}
    assert labels[catalog.get(UNEMPLOYMENT).rerank_text()] == 1.0
    assert labels[catalog.get(LIFE).rerank_text()] == 0.0


def test_a_claim_the_catalog_has_nothing_for_gives_only_negatives(
    claims: list[Claim], catalog: Catalog
) -> None:
    groups = build_groups(claims, [], catalog, FixedSearch([(UNEMPLOYMENT, 0.8), (DEBT, 0.7)]))
    unicorns = next(g for g in groups if g.query.claim.key == "d3#1")
    assert unicorns.gold is None and unicorns.training_ids == unicorns.ids
    assert [p.label for p in pairs([unicorns], catalog)] == [0.0, 0.0]


def test_pairs_read_the_query_sentence_and_the_rerank_text(
    claims: list[Claim], catalog: Catalog
) -> None:
    groups = build_groups(
        claims, [para("d1#1", "Jobless rate, Italy, 2022: 8%")], catalog, FixedSearch([(LIFE, 1)])
    )
    paraphrased = next(g for g in groups if g.query.paraphrase)
    assert {(p.query, p.document) for p in pairs([paraphrased], catalog)} == {
        ("Jobless rate, Italy, 2022: 8%", catalog.get(LIFE).rerank_text()),
        ("Jobless rate, Italy, 2022: 8%", catalog.get(UNEMPLOYMENT).rerank_text()),
    }


class LetterEmbedder:
    """Unit vectors of letter counts: deterministic and offline."""

    dim = 26

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out = []
        for text in texts:
            counts = [float(text.lower().count(chr(97 + i))) for i in range(26)]
            norm = math.sqrt(sum(x * x for x in counts)) or 1.0
            out.append([x / norm for x in counts])
        return out


def test_embedding_search_returns_the_pipeline_pool_best_first(catalog: Catalog) -> None:
    search = embedding_search(catalog, LetterEmbedder())
    [pool] = search(["unemployment rate"])
    assert len(pool) == min(SEARCH_POOL, len(catalog.indicators))
    scores = [s for _, s in pool]
    assert scores == sorted(scores, reverse=True)
    assert len({i for i, _ in pool}) == len(pool)
