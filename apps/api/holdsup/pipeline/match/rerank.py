"""The reranker's turn: order the covering candidates by how well each fits the claim, and
say whether that order is clear enough to skip the model ("model only if margin low").

The reranker reads the claim's sentence beside each candidate's `rerank_text()`, the pairs it
was trained on (ml/reranker). Its margin is the first candidate's probability minus the
second's (minus 0 when only one candidate covers the place).
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from holdsup.catalog.index import IndicatorHit
from holdsup.catalog.schema import Catalog

# From the margin table in ml/reranker/reports/report.md (out-of-fold ranks on the dev split):
# 52% of claims have a margin of at least 0.5, and the reranker's first pick is right on 96.4%
# of them. P4.7 tunes it on the dev split; a retrained model needs its own table.
SKIP_MARGIN = 0.5


class Reranker(Protocol):
    @property
    def model(self) -> str: ...  # what receipts call it (the pinned repo@revision)

    def probabilities(self, query: str, documents: Sequence[str]) -> list[float]: ...


@dataclass(frozen=True)
class Ranked:
    model: str  # the reranker that ranked them
    hits: list[IndicatorHit]  # best first
    probabilities: list[float]  # in the same order

    @property
    def margin(self) -> float:
        if not self.probabilities:
            return 0.0
        second = self.probabilities[1] if len(self.probabilities) > 1 else 0.0
        return self.probabilities[0] - second


async def rerank(
    reranker: Reranker, quote: str, hits: Sequence[IndicatorHit], catalog: Catalog
) -> Ranked:
    """`hits` best first by the reranker; equal scores keep the search's order."""
    documents = [catalog.get(h.id).rerank_text() for h in hits]
    # Scoring is CPU-bound (about 160 ms for 8 candidates); keep it off the event loop.
    scores = await asyncio.to_thread(reranker.probabilities, quote, documents)
    order = sorted(range(len(hits)), key=lambda i: -scores[i])
    return Ranked(reranker.model, [hits[i] for i in order], [scores[i] for i in order])
