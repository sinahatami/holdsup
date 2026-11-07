"""Claim place codes ↔ each source's codes."""

import pytest

from holdsup.adapters.base import Observation
from holdsup.catalog.schema import Source
from holdsup.geo import (
    ISO2,
    ISO3,
    UnknownPlace,
    from_source,
    geo_filter,
    to_claim_codes,
    to_source,
)


def test_the_iso_table_is_one_to_one() -> None:
    assert len(ISO3) == len(ISO2) == 250
    assert ISO3["GB"] == "GBR" and ISO3["GR"] == "GRC" and ISO3["DE"] == "DEU"


@pytest.mark.parametrize(
    ("source", "code", "expected"),
    [
        (Source.EUROSTAT, "IT", "IT"),
        (Source.EUROSTAT, "GR", "EL"),
        (Source.EUROSTAT, "GB", "UK"),
        (Source.EUROSTAT, "EU", "EU27_2020"),
        (Source.EUROSTAT, "EA", "EA20"),
        (Source.WORLDBANK, "IT", "IT"),
        (Source.WORLDBANK, "WORLD", "WLD"),
        (Source.WORLDBANK, "EU", "EUU"),
        (Source.OWID, "IT", "ITA"),
        (Source.OWID, "WORLD", "OWID_WRL"),
        (Source.OWID, "XK", "OWID_KOS"),
    ],
)
def test_to_source(source: Source, code: str, expected: str) -> None:
    assert to_source(source, code) == expected


@pytest.mark.parametrize("code", ["G7", "OECD", "ZZ"])
def test_unknown_places(code: str) -> None:
    with pytest.raises(UnknownPlace, match=code):
        to_source(Source.EUROSTAT, code)


def test_geo_filter_one_or_many_places() -> None:
    assert geo_filter(Source.EUROSTAT, ["IT"]) == {"geo": "IT"}
    assert geo_filter(Source.OWID, ["IT", "FR", "IT"]) == {"country": ["ITA", "FRA"]}
    assert geo_filter(Source.WORLDBANK, ["WORLD"]) == {"country": "WLD"}
    with pytest.raises(UnknownPlace, match="no place"):
        geo_filter(Source.EUROSTAT, [])
    with pytest.raises(UnknownPlace, match="no adapter"):
        geo_filter(Source("datacommons"), ["IT"])


@pytest.mark.parametrize(
    ("source", "observation", "expected"),
    [
        (Source.EUROSTAT, Observation("EL", "2024", 1.0), "GR"),
        (Source.EUROSTAT, Observation("EU27_2020", "2024", 1.0), "EU"),
        (Source.EUROSTAT, Observation("IT", "2024", 1.0), "IT"),
        # World Bank: read the ISO3 dimension (country.id is "1W" for the world).
        (Source.WORLDBANK, Observation("1W", "2024", 1.0, dims={"iso3": "WLD"}), "WORLD"),
        (Source.WORLDBANK, Observation("IT", "2024", 1.0, dims={"iso3": "ITA"}), "IT"),
        (Source.WORLDBANK, Observation("XC", "2024", 1.0, dims={"iso3": "EMU"}), "EA"),
        (Source.WORLDBANK, Observation("IT", "2024", 1.0), "IT"),
        (Source.OWID, Observation("ITA", "2024", 1.0), "IT"),
        (Source.OWID, Observation("OWID_WRL", "2024", 1.0), "WORLD"),
        (Source.OWID, Observation("Africa", "2024", 1.0), "Africa"),
    ],
)
def test_from_source(source: Source, observation: Observation, expected: str) -> None:
    assert from_source(source, observation) == expected


def test_to_claim_codes_keeps_everything_else() -> None:
    rows = [Observation("EL", "2024", 1.5, "p", {"age": "Y15-74"}), Observation("IT", "2024", None)]
    out = to_claim_codes(Source.EUROSTAT, rows)
    assert out[0] == Observation("GR", "2024", 1.5, "p", {"age": "Y15-74"})
    assert out[1] is rows[1]
