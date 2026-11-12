"""What adjusts money at current prices for inflation, for the real-terms check (P3.4, D026).

An entry marked `nominal` in the catalog is checked again after inflation: on its own real
version when the catalog has one (nominal GDP → GDP in chain-linked volumes), otherwise, for a
yearly series, deflated by the place's consumer prices (the World Bank's yearly CPI inflation,
chained into an index by `ops.chain_index`). Half-yearly prices have no fitting index yet.
"""

from holdsup.catalog.coverage import covers
from holdsup.catalog.schema import Catalog, Frequency, IndicatorSpec

PRICE_RATES_ID = "cpi_inflation_annual"


def real_terms_source(
    catalog: Catalog, spec: IndicatorSpec, geo: str | None
) -> IndicatorSpec | None:
    """The entry the real-terms check reads for `spec` in `geo`: its real version, or consumer
    price inflation; None when neither fits."""
    if not spec.nominal:
        return None
    if spec.real_version is not None:
        real = catalog.get(spec.real_version)
        return real if covers(real.geo_coverage, geo) else None
    if spec.frequency is not Frequency.ANNUAL:
        return None
    try:
        prices = catalog.get(PRICE_RATES_ID)
    except KeyError:
        return None
    return prices if covers(prices.geo_coverage, geo) else None
