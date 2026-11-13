"""Print what the data adapters return for catalog indicators, to label benchmark claims by hand (P4.1).

Offline tooling like record_series.py: it hits the network, nothing in a request path imports it.
Put it in apps/api/scripts/ and run it the way `make record-series` runs record_series.py
(see the Makefile), with indicator:geo pairs:

    peek_series.py unemployment_rate_monthly:IT government_debt_pct_gdp:FR

For each pair it prints one block: the catalog unit, the source's update date, the coverage,
the latest observation (period and value, for "latest" and release-lag questions) and the
yearly figures since --from (default 2000). A year is made from the series' observations by the
catalog's `annual_value` rule (mean, last or sum); the rule used is printed, because the pipeline
is what decides in the end: check a borderline figure against the receipt. A pair the source
cannot serve prints the error and the run goes on, so the output also shows which place and
period are missing (the cant_check cases).
"""

import argparse
import asyncio
import sys
from collections import defaultdict

import httpx

from holdsup.adapters.eurostat import EurostatAdapter
from holdsup.adapters.owid import OwidAdapter
from holdsup.adapters.worldbank import WorldBankAdapter
from holdsup.catalog.schema import load_catalog
from holdsup.config import REPO_ROOT
from holdsup.geo import geo_filter


def yearly(observations, rule: str) -> dict[str, float]:
    by_year: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for o in observations:
        if o.value is not None:
            by_year[str(o.period)[:4]].append((str(o.period), float(o.value)))
    out: dict[str, float] = {}
    for year, rows in by_year.items():
        rows.sort()
        values = [v for _, v in rows]
        if rule == "last":
            out[year] = values[-1]
        elif rule == "sum":
            out[year] = sum(values)
        else:
            out[year] = sum(values) / len(values)
    return out


def fmt(value: float) -> str:
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.2f}"


async def main(pairs: list[tuple[str, str]], first: int) -> int:
    catalog = load_catalog(REPO_ROOT / "packages" / "catalog")
    async with httpx.AsyncClient(timeout=60.0) as http:
        adapters = {
            "eurostat": EurostatAdapter(http),
            "worldbank": WorldBankAdapter(http),
            "owid": OwidAdapter(http),
        }
        for indicator_id, geo in pairs:
            head = f"== {indicator_id}:{geo}"
            try:
                spec = catalog.get(indicator_id)
                filters = {**spec.filters, **geo_filter(spec.source, [geo])}
                series = await adapters[str(spec.source)].fetch_series(spec.source_code, filters)
            except Exception as exc:  # noqa: BLE001 - one missing series must not stop the run
                print(f"{head}\n   ERROR {type(exc).__name__}: {exc}\n")
                continue
            rule = str(getattr(spec, "annual_value", "mean"))
            seen = sorted(
                (str(o.period), float(o.value)) for o in series.observations if o.value is not None
            )
            print(
                f"{head}  [{getattr(spec, 'unit', '?')}]  freq={getattr(spec, 'frequency', '?')}"
                f"  annual={rule}  updated={series.updated}"
            )
            if not seen:
                print("   no values\n")
                continue
            print(
                f"   coverage {seen[0][0]}..{seen[-1][0]}   latest {seen[-1][0]} = {fmt(seen[-1][1])}"
            )
            years = yearly(series.observations, rule)
            line = "  ".join(f"{y}={fmt(v)}" for y, v in sorted(years.items()) if int(y) >= first)
            print(f"   {line}\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pairs", nargs="+", help="indicator_id:GEO, for example co2_per_capita:US")
    parser.add_argument("--from", dest="first", type=int, default=2000)
    args = parser.parse_args()
    wanted = [tuple(p.split(":", 1)) for p in args.pairs]
    sys.exit(asyncio.run(main([(a, b) for a, b in wanted], args.first)))
