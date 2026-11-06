"""Vector search over the catalog: pgvector in production, in-memory for tests and scripts."""

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from holdsup.catalog.embed import Embedder
from holdsup.catalog.schema import IndicatorSpec
from holdsup.db.models import Indicator


class IndicatorHit(BaseModel):
    id: str
    name: str
    source: str
    source_code: str
    unit: str
    frequency: str
    definition: str
    score: float  # cosine similarity, higher is closer


def _hit(spec: IndicatorSpec | Indicator, score: float) -> IndicatorHit:
    return IndicatorHit(
        id=spec.id,
        name=spec.name,
        source=str(spec.source),
        source_code=spec.source_code,
        unit=spec.unit,
        frequency=str(spec.frequency),
        definition=spec.definition,
        score=round(score, 4),
    )


@dataclass
class InMemoryIndex:
    specs: Sequence[IndicatorSpec]
    vectors: Sequence[Sequence[float]]

    @classmethod
    def build(cls, specs: Sequence[IndicatorSpec], embedder: Embedder) -> "InMemoryIndex":
        return cls(specs, embedder.embed([s.embedding_text() for s in specs]))

    def search(self, query_vector: Sequence[float], k: int) -> list[IndicatorHit]:
        scored = [
            (sum(a * b for a, b in zip(query_vector, v, strict=True)), spec)
            for spec, v in zip(self.specs, self.vectors, strict=True)
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [_hit(spec, score) for score, spec in scored[:k]]


class SqlIndex:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def search(self, query_vector: Sequence[float], k: int) -> list[IndicatorHit]:
        distance = Indicator.embedding.cosine_distance(list(query_vector))
        stmt = select(Indicator, distance.label("distance")).order_by(distance).limit(k)
        async with self._sessionmaker() as session:
            rows = (await session.execute(stmt)).all()
        return [_hit(row.Indicator, 1.0 - float(row.distance)) for row in rows]
