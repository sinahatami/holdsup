"""Record what the data adapters return for catalog indicators, for pipeline regression tests.

Usage (from the repo root):  make record-series [ARGS="youth_unemployment_rate_monthly:IT"]
With no arguments, every entry in SERIES is re-recorded. Each file holds the adapter's
FetchedSeries for one indicator and place (observations in the source's own codes, as the
pipeline receives them), so a test can serve it as the fetcher would. Tests never hit the
network; this script does.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

from holdsup.adapters.base import FetchedSeries, Filters
from holdsup.adapters.eurostat import EurostatAdapter
from holdsup.adapters.owid import OwidAdapter
from holdsup.adapters.worldbank import WorldBankAdapter
from holdsup.catalog.schema import load_catalog
from holdsup.config import REPO_ROOT
from holdsup.geo import geo_filter

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "series"

# indicator id: place. The regression claims in tests/pipeline/test_regressions.py.
SERIES = [
    ("unemployment_rate_monthly", "IT"),  # r001
    ("youth_unemployment_rate_monthly", "IT"),  # c001, c002, c004
    ("government_debt_pct_gdp", "IT"),  # c006, c007
    ("government_debt_pct_gdp_quarterly", "IT"),  # c006
    ("greenhouse_gas_emissions", "IT"),  # c018
    ("co2_per_capita", "US"),  # c024
    ("unemployment_rate_ilo", "ZA"),  # c029
    ("population_total", "IT"),  # p001, and the denominator fetched for c018
]


def path_for(indicator_id: str, geo: str) -> Path:
    return OUT / f"{indicator_id}.{geo}.json"


def dump(indicator_id: str, geo: str, filters: Filters, s: FetchedSeries) -> str:
    doc = {
        "indicator": indicator_id,
        "geo": geo,
        "source": s.source,
        "dataset": s.dataset,
        "filters": dict(filters),
        "url": s.url,
        "retrieved_at": s.retrieved_at.isoformat(),
        "raw_sha256": s.raw_sha256,
        "label": s.label,
        "updated": s.updated,
        "citation": s.citation,
        "observations": [[o.geo, o.period, o.value] for o in s.observations],
    }
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


async def main(wanted: list[tuple[str, str]]) -> int:
    catalog = load_catalog(REPO_ROOT / "packages" / "catalog")
    OUT.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=60.0) as http:
        adapters: dict[str, EurostatAdapter | WorldBankAdapter | OwidAdapter] = {
            "eurostat": EurostatAdapter(http),
            "worldbank": WorldBankAdapter(http),
            "owid": OwidAdapter(http),
        }
        for indicator_id, geo in wanted:
            spec = catalog.get(indicator_id)
            filters = {**spec.filters, **geo_filter(spec.source, [geo])}
            series = await adapters[str(spec.source)].fetch_series(spec.source_code, filters)
            path_for(indicator_id, geo).write_text(dump(indicator_id, geo, filters, series))
            rows = sum(o.value is not None for o in series.observations)
            print(f"{indicator_id}.{geo}: {rows} values, updated {series.updated}")
    return 0


if __name__ == "__main__":
    args = [tuple(a.split(":", 1)) for a in sys.argv[1:]]
    sys.exit(asyncio.run(main([(a[0], a[1]) for a in args] or SERIES)))
