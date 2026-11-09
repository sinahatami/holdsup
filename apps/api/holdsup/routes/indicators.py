"""GET /v1/indicators?q= : vector search over the catalog."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from holdsup.catalog.coverage import places
from holdsup.catalog.index import IndicatorHit
from holdsup.catalog.schema import IndicatorSpec, Theme
from holdsup.routes.deps import CatalogDep, Search

router = APIRouter(tags=["catalog"])


class IndicatorSearchResponse(BaseModel):
    query: str
    results: list[IndicatorHit]


class CatalogEntry(BaseModel):
    id: str
    name: str
    theme: Theme  # the topic it is listed under; the page names and orders the themes
    definition: str
    unit: str
    source: str
    frequency: str
    first_year: int
    last_year: int | None
    source_code: str  # the source's own name for the series, to find it there
    aliases: list[str]  # other ways of saying it, so a search finds it
    countries: list[str]  # ISO codes of the countries named; see all_countries
    groups: list[str]  # the groups it covers as a whole: EU, EA, WORLD
    all_countries: bool  # True when every country is covered, not only those in `countries`


class CatalogResponse(BaseModel):
    version: str
    indicators: list[CatalogEntry]


def _entry(s: IndicatorSpec) -> CatalogEntry:
    countries, groups, every = places(s.geo_coverage)
    return CatalogEntry(
        id=s.id,
        name=s.name,
        theme=s.theme,
        definition=s.definition,
        unit=s.unit,
        source=s.source.label,
        frequency=str(s.frequency),
        first_year=s.first_year,
        last_year=s.last_year,
        source_code=s.source_code,
        aliases=list(s.aliases),
        countries=countries,
        groups=groups,
        all_countries=every,
    )


@router.get("/catalog", response_model=CatalogResponse)
async def list_catalog(catalog: CatalogDep) -> CatalogResponse:
    """Everything HoldsUp can check, A to Z."""
    entries = [_entry(s) for s in sorted(catalog.indicators, key=lambda s: s.name.casefold())]
    return CatalogResponse(version=catalog.version, indicators=entries)


@router.get("/indicators", response_model=IndicatorSearchResponse)
async def search_indicators(
    search: Search,
    q: Annotated[str, Query(min_length=2, max_length=200, description="What to look for")],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> IndicatorSearchResponse:
    return IndicatorSearchResponse(query=q, results=await search(q.strip(), limit))
