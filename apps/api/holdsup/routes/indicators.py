"""GET /v1/indicators?q= : vector search over the catalog."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from holdsup.catalog.index import IndicatorHit
from holdsup.routes.deps import Search

router = APIRouter(tags=["catalog"])


class IndicatorSearchResponse(BaseModel):
    query: str
    results: list[IndicatorHit]


@router.get("/indicators", response_model=IndicatorSearchResponse)
async def search_indicators(
    search: Search,
    q: Annotated[str, Query(min_length=2, max_length=200, description="What to look for")],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> IndicatorSearchResponse:
    return IndicatorSearchResponse(query=q, results=await search(q.strip(), limit))
