"""Phrase search over the catalog: embed the phrase, then ask a vector index.

`vector_search` builds the one `CatalogSearch` that both the `/v1/indicators` route and the
match step use, whichever index backs it (pgvector in production, in memory in tests).
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from holdsup.catalog.embed import Embedder
from holdsup.catalog.index import IndicatorHit

CatalogSearch = Callable[[str, int], Awaitable[list[IndicatorHit]]]


def vector_search(
    index_search: Callable[[Sequence[float], int], Any], embedder: Embedder
) -> CatalogSearch:
    """Wrap an index's `search` (sync in memory, async in Postgres) as a phrase search."""

    async def search(phrase: str, k: int) -> list[IndicatorHit]:
        # Embedding is CPU-bound; keep it off the event loop.
        [vector] = await asyncio.to_thread(embedder.embed, [phrase])
        hits = index_search(vector, k)
        if isinstance(hits, Awaitable):
            hits = await hits
        return list(hits)

    return search
