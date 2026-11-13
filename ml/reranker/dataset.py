"""Query groups: a claim sentence and the candidates the pipeline would show for it.

A query is a dev claim's quote or one of its paraphrases. Its candidates are what matching
reads first: the catalog search's pool, kept to entries that cover the claim's place, top 8
(holdsup.pipeline.match.candidates). The labelled indicator is the positive and the rest are
hard negatives. When the search missed the labelled indicator, training still gets it as a
positive (`Group.training_ids`); scoring never does, so recall@8 stays the search's own.
A claim the catalog has nothing for gives a group with no positive at all, which is what the
reranker should learn to score low across the board.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from holdsup.catalog.coverage import covers
from holdsup.catalog.embed import Embedder
from holdsup.catalog.index import InMemoryIndex
from holdsup.catalog.schema import Catalog
from holdsup.pipeline.match.candidates import SEARCH_POOL, TOP_K
from reranker.benchmark import Claim, dev
from reranker.leakage import check_training_sentences
from reranker.paraphrase import Paraphrase

# Sentences in, for each the search pool (catalog id, similarity), best first.
Search = Callable[[Sequence[str]], list[list[tuple[str, float]]]]


@dataclass(frozen=True)
class Query:
    claim: Claim
    text: str
    paraphrase: bool  # False: the labelled quote itself


@dataclass(frozen=True)
class Group:
    query: Query
    ids: tuple[str, ...]  # the top 8 shown, in search order
    similarities: tuple[float, ...]  # the search's cosine similarity, same order

    @property
    def gold(self) -> str | None:
        return self.query.claim.indicator

    @property
    def training_ids(self) -> tuple[str, ...]:
        """The candidates plus the labelled indicator when the search missed it."""
        if self.gold is None or self.gold in self.ids:
            return self.ids
        return (*self.ids, self.gold)


@dataclass(frozen=True)
class Pair:
    query: str
    document: str
    label: float  # 1.0 for the labelled indicator


def embedding_search(catalog: Catalog, embedder: Embedder) -> Search:
    """The pipeline's search, over the catalog in memory: same embedder, same texts."""
    index = InMemoryIndex.build(catalog.indicators, embedder)

    def search(sentences: Sequence[str]) -> list[list[tuple[str, float]]]:
        vectors = embedder.embed(list(sentences))
        return [[(h.id, h.score) for h in index.search(v, SEARCH_POOL)] for v in vectors]

    return search


def queries(claims: Sequence[Claim], paraphrases: Sequence[Paraphrase]) -> list[Query]:
    """Every dev quote, then every paraphrase. Raises LeakageError if any of them is, or
    rewords, a held-out claim."""
    by_key = {c.key: c for c in dev(claims)}
    check_training_sentences(
        [(c.key, c.quote) for c in by_key.values()] + [(p.claim, p.text) for p in paraphrases],
        claims,
    )
    return [Query(c, c.quote, False) for c in by_key.values()] + [
        Query(by_key[p.claim], p.text, True) for p in paraphrases
    ]


def build_groups(
    claims: Sequence[Claim],
    paraphrases: Sequence[Paraphrase],
    catalog: Catalog,
    search: Search,
) -> list[Group]:
    qs = queries(claims, paraphrases)
    groups: list[Group] = []
    for q, pool in zip(qs, search([q.text for q in qs]), strict=True):
        kept = [(i, s) for i, s in pool if covers(catalog.get(i).geo_coverage, q.claim.geo)]
        top = kept[:TOP_K]
        groups.append(Group(q, tuple(i for i, _ in top), tuple(s for _, s in top)))
    return groups


def pairs(groups: Sequence[Group], catalog: Catalog) -> list[Pair]:
    return [
        Pair(g.query.text, catalog.get(i).rerank_text(), 1.0 if i == g.gold else 0.0)
        for g in groups
        for i in g.training_ids
    ]
