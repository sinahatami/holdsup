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
