"""Record raw data-source responses as test fixtures (CLAUDE.md: tests never hit the network).

Usage (from apps/api):  uv run python -m scripts.record_fixture [name ...]
With no names, every fixture in FIXTURES is re-recorded. Bodies are saved byte-for-byte so
the raw-response hash in tests matches what the adapter would compute live.
"""

import sys
from pathlib import Path

import httpx

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
WORLDBANK = "https://api.worldbank.org/v2"
OWID = "https://ourworldindata.org/grapher"

# name -> URL. Keep queries small: fixtures are committed.
FIXTURES: dict[str, str] = {
    # Monthly, 3 geos, some missing cells and one time position with no data at all.
    "eurostat/une_rt_m_youth_monthly.json": (
        f"{EUROSTAT}/une_rt_m?format=JSON&lang=EN&geo=EU27_2020&geo=IT&geo=CH"
        "&sex=T&age=Y_LT25&unit=PC_ACT&s_adj=SA&sinceTimePeriod=2025-01"
    ),
    # Annual, 3 geos, status flags (b = break in series, d = definition differs).
    "eurostat/une_rt_a_annual.json": (
        f"{EUROSTAT}/une_rt_a?format=JSON&lang=EN&geo=IT&geo=DE&geo=FR"
        "&sex=T&age=Y15-74&unit=PC_ACT&sinceTimePeriod=2014"
    ),
    # Annual GDP with a missing value (LI) and flags (p = provisional, e = estimated).
    "eurostat/nama_10_gdp_missing.json": (
        f"{EUROSTAT}/nama_10_gdp?format=JSON&lang=EN&geo=IT&geo=MT&geo=LI"
        "&na_item=B1GQ&unit=CP_MEUR&sinceTimePeriod=2018"
    ),
    # Error body for an unknown dataset (HTTP 404).
    "eurostat/error_not_found.json": f"{EUROSTAT}/no_such_dataset?format=JSON&lang=EN",
    # World Bank: two countries, annual, all values present.
    "worldbank/youth_unemployment_it_de.json": (
        f"{WORLDBANK}/country/IT;DE/indicator/SL.UEM.1524.ZS?format=json&per_page=1000&date=2010:2025"
    ),
    # World Bank: Gini index for Italy has gaps (null values).
    "worldbank/gini_it_gaps.json": (
        f"{WORLDBANK}/country/IT/indicator/SI.POV.GINI?format=json&per_page=1000&date=2000:2024"
    ),
    # World Bank error block: HTTP 200 with a "message" array for a bad indicator code.
    "worldbank/error_invalid_indicator.json": (
        f"{WORLDBANK}/country/IT/indicator/NOT.A.CODE?format=json&per_page=1000"
    ),
    # World Bank: unknown country -> HTTP 200, total 0, data null.
    "worldbank/empty_unknown_country.json": (
        f"{WORLDBANK}/country/XX/indicator/SL.UEM.1524.ZS?format=json&per_page=1000"
    ),
    # OWID chart CSV (filtered to two countries) and its metadata.
    "owid/co2_per_capita_it_de.csv": (
        f"{OWID}/co2-emissions-per-capita.csv?v=1&csvType=filtered&useColumnShortNames=true"
        "&country=ITA~DEU&time=2015..2023"
    ),
    "owid/co2_per_capita.metadata.json": (
        f"{OWID}/co2-emissions-per-capita.metadata.json?v=1&csvType=filtered&useColumnShortNames=true"
    ),
    # OWID entity without ISO code (price benchmark), so geo falls back to the entity name.
    "owid/natural_gas_prices.csv": (
        f"{OWID}/natural-gas-prices.csv?v=1&csvType=filtered&useColumnShortNames=true"
    ),
    # OWID unknown chart (HTTP 404).
    "owid/error_not_found.csv": (
        f"{OWID}/no-such-chart-holdsup.csv?v=1&csvType=filtered&useColumnShortNames=true"
    ),
    # OWID old slug that redirects (301) to a multi-view chart: renewable-share-energy ->
    # energy-mix?metric=share&source=renewables. Recorded after the redirect, with tab=chart.
    "owid/energy_mix_renewables_share_de_it.csv": (
        f"{OWID}/renewable-share-energy.csv?v=1&csvType=filtered&useColumnShortNames=true"
        "&tab=chart&country=DEU~ITA&time=2015..2024"
    ),
    "owid/energy_mix_renewables_share.metadata.json": (
        f"{OWID}/energy-mix.metadata.json?v=1&useColumnShortNames=true"
        "&metric=share&source=renewables"
    ),
    # The same chart without tab=chart: the map's latest-year snapshot of every country,
    # which ignores country and time (what the adapter got before tab=chart).
    "owid/energy_mix_renewables_share_map_snapshot.csv": (
        f"{OWID}/energy-mix.csv?v=1&csvType=filtered&useColumnShortNames=true"
        "&metric=share&source=renewables&country=DEU~ITA&time=2015..2024"
    ),
    # NOTE: owid/error_403_not_redistributable.txt is hand-written (no public chart that
    # returns 403 was found on 2026-11-06); it is not in this manifest.
}


def record(name: str) -> None:
    url = FIXTURES[name]
    response = httpx.get(url, timeout=60, follow_redirects=True)
    path = FIXTURE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print(f"{response.status_code} {len(response.content):>7} bytes  {name}")


def main(names: list[str]) -> int:
    for name in names or list(FIXTURES):
        record(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
