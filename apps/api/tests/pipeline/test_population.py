"""The population denominator: which entry serves a place, and which series divide by it."""

import pytest

from holdsup.catalog.schema import Source, load_catalog
from holdsup.config import REPO_ROOT
from holdsup.pipeline.population import population_for, wants_population
from holdsup.pipeline.result import app_version
from holdsup.places import place_name

CATALOG = load_catalog(REPO_ROOT / "packages" / "catalog")


@pytest.mark.parametrize(
    ("geo", "expected"),
    [
        ("IT", "population_total"),  # Eurostat for the European countries
        ("EU", "population_total"),
        ("NO", "population_total"),
        ("US", "population_total_world"),  # the World Bank for the rest
        ("ZA", "population_total_world"),
        ("WORLD", "population_total_world"),
    ],
)
def test_population_comes_from_eurostat_in_europe_and_the_world_bank_elsewhere(
    geo: str, expected: str
) -> None:
    spec = population_for(CATALOG, geo)
    assert spec is not None and spec.id == expected


def test_no_place_no_population() -> None:
    assert population_for(CATALOG, None) is None
    assert population_for(CATALOG, "G7") is None


def test_the_two_entries_cite_their_sources() -> None:
    assert [(s.source, s.source_code) for s in map(CATALOG.get, ("population_total", "population_total_world"))] == [
        (Source.EUROSTAT, "demo_pjan"),
        (Source.WORLDBANK, "SP.POP.TOTL"),
    ]  # fmt: skip


def test_only_yearly_amounts_and_counts_are_divided_by_population() -> None:
    wanted = {s.id for s in CATALOG.indicators if wants_population(s)}
    assert {"greenhouse_gas_emissions", "live_births", "nominal_gdp_eur"} <= wanted
    assert not wanted & {"population_total", "population_total_world", "co2_per_capita"}
    assert not wanted & {
        "unemployment_rate_monthly",
        "government_debt_pct_gdp",
        "hicp_inflation_monthly",
    }


def test_place_names_for_readers() -> None:
    assert place_name("IT") == "Italy"
    assert place_name("ZZ") == "ZZ"


def test_source_labels() -> None:
    assert Source.WORLDBANK.label == "the World Bank"


def test_app_version_names_the_commit_when_it_is_known(monkeypatch: pytest.MonkeyPatch) -> None:
    from holdsup.config import get_settings

    monkeypatch.setenv("APP_COMMIT", "d264e60abc123")
    get_settings.cache_clear()
    try:
        assert app_version().endswith("+d264e60")
        monkeypatch.setenv("APP_COMMIT", "")
        get_settings.cache_clear()
        assert "+" not in app_version()
    finally:
        get_settings.cache_clear()
