"""The candidates a model may pick from: catalog search kept to entries that cover the place."""

from dataclasses import dataclass

from holdsup.catalog.coverage import covers
from holdsup.catalog.index import IndicatorHit
from holdsup.catalog.schema import Catalog, IndicatorSpec
from holdsup.catalog.search import CatalogSearch

TOP_K = 8
SEARCH_POOL = 40  # vector hits read before the coverage filter keeps the top 8


@dataclass(frozen=True)
class CandidatePool:
    catalog: Catalog
    search: CatalogSearch

    def covers(self, spec: IndicatorSpec, geo: str | None) -> bool:
        return covers(spec.geo_coverage, geo)

    async def covering(self, phrase: str, geo: str | None) -> tuple[list[IndicatorHit], list[str]]:
        """The top hits for `phrase` that cover `geo`, and the ids of hits dropped for not."""
        hits = await self.search(phrase, SEARCH_POOL)
        kept: list[IndicatorHit] = []
        dropped: list[IndicatorHit] = []
        for hit in hits:
            (kept if self.covers(self.catalog.get(hit.id), geo) else dropped).append(hit)
        return kept[:TOP_K], [h.id for h in dropped]
