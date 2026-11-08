"""Factory for the live data-source adapters: one per catalog `Source` that has one.

Adding a source is one entry in `ADAPTER_FACTORIES`; the wiring and the cache pick it up from
here. A source with no entry (Data Commons, for now) has catalog entries but cannot be fetched.
"""

from collections.abc import Callable, Mapping

import httpx

from holdsup.adapters.base import SeriesAdapter
from holdsup.adapters.eurostat import EurostatAdapter
from holdsup.adapters.owid import OwidAdapter
from holdsup.adapters.worldbank import WorldBankAdapter
from holdsup.catalog.schema import Source

type AdapterFactory = Callable[[httpx.AsyncClient], SeriesAdapter]

ADAPTER_FACTORIES: Mapping[Source, AdapterFactory] = {
    Source.EUROSTAT: EurostatAdapter,
    Source.WORLDBANK: WorldBankAdapter,
    Source.OWID: OwidAdapter,
}


def build_adapters(http: httpx.AsyncClient) -> dict[str, SeriesAdapter]:
    """One adapter per supported source, all sharing `http`, keyed by source name."""
    return {str(source): make(http) for source, make in ADAPTER_FACTORIES.items()}
