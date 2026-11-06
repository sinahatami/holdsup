"""GET /v1/indicators?q= : vector search over the catalog."""

import asyncio
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from holdsup.catalog.embed import Embedder, default_embedder
from holdsup.catalog.index import IndicatorHit, SqlIndex
from holdsup.config import get_settings
from holdsup.db.session import get_sessionmaker

router = APIRouter(tags=["catalog"])


class IndicatorSearchResponse(BaseModel):
    query: str
    results: list[IndicatorHit]


class Searcher(Protocol):
    async def search(self, query: str, k: int) -> list[IndicatorHit]: ...


class CatalogSearch:
    def __init__(self, embedder: Embedder, index: SqlIndex) -> None:
        self._embedder = embedder
        self._index = index

    async def search(self, query: str, k: int) -> list[IndicatorHit]:
        # Embedding is CPU-bound; keep it off the event loop.
        [vector] = await asyncio.to_thread(self._embedder.embed, [query])
        return await self._index.search(vector, k)


def get_searcher() -> Searcher:
    embedder = default_embedder(get_settings().fastembed_cache_path)
    return CatalogSearch(embedder, SqlIndex(get_sessionmaker()))


@router.get("/indicators", response_model=IndicatorSearchResponse)
async def search_indicators(
    searcher: Annotated[Searcher, Depends(get_searcher)],
    q: Annotated[str, Query(min_length=2, max_length=200, description="What to look for")],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> IndicatorSearchResponse:
    return IndicatorSearchResponse(query=q, results=await searcher.search(q.strip(), limit))
