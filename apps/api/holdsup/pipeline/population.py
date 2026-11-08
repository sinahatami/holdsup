"""The population denominator: which catalog entry gives a place's total population.

Eurostat's `demo_pjan` covers the European countries; the World Bank's `SP.POP.TOTL` covers the
rest. The per-capita operation reads it through the plan's `others`; the distortion check
(P3.4) asks the same question, so both use `population_for`.
"""

from holdsup.catalog.coverage import covers
from holdsup.catalog.schema import Catalog, Frequency, IndicatorSpec

# Preference order: the first entry that covers the place.
POPULATION_IDS = ("population_total", "population_total_world")


def population_for(catalog: Catalog, geo: str | None) -> IndicatorSpec | None:
    """The total-population entry with data for `geo`, or None."""
    if geo is None:
        return None
    for indicator_id in POPULATION_IDS:
        spec = catalog.get(indicator_id)
        if covers(spec.geo_coverage, geo):
            return spec
    return None


def wants_population(spec: IndicatorSpec) -> bool:
    """True when dividing `spec` by population could mean something: a yearly amount or count,
    not a rate, a share, a per-person figure or a population itself."""
    unit = spec.unit.strip().lower()
    return (
        spec.frequency is Frequency.ANNUAL
        and spec.id not in POPULATION_IDS
        and not unit.startswith("%")
        and " per " not in unit
        and "index" not in unit
    )
