"""vector_search: one phrase search over a sync (in-memory) or async (pgvector) index."""

from collections.abc import Sequence

from holdsup.catalog.index import IndicatorHit, InMemoryIndex
from holdsup.catalog.schema import load_catalog
from holdsup.catalog.search import vector_search
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder

EMBEDDER = HashEmbedder()
INDEX = InMemoryIndex.build(load_catalog(FIXTURE_CATALOG).indicators, EMBEDDER)


async def test_vector_search_reads_a_sync_index() -> None:
    hits = await vector_search(INDEX.search, EMBEDDER)("youth unemployment rate", 2)
    assert hits[0].id == "youth_unemployment_rate" and len(hits) == 2


async def test_vector_search_accepts_an_async_index() -> None:
    async def search(vector: Sequence[float], k: int) -> list[IndicatorHit]:
        return INDEX.search(vector, k)

    hits = await vector_search(search, EMBEDDER)("youth unemployment rate", 2)
    assert hits[0].id == "youth_unemployment_rate" and len(hits) == 2
