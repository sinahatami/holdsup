"""A reranker that answers from a table, for match and pipeline tests (no model file)."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from holdsup.catalog.schema import Catalog


@dataclass
class FakeReranker:
    catalog: Catalog
    by_id: dict[str, float]  # indicator id -> probability (0 when not listed)
    model: str = "fake/reranker@0000000"
    queries: list[str] = field(default_factory=list)

    def probabilities(self, query: str, documents: Sequence[str]) -> list[float]:
        self.queries.append(query)
        ids = {spec.rerank_text(): spec.id for spec in self.catalog.indicators}
        return [self.by_id.get(ids[d], 0.0) for d in documents]
